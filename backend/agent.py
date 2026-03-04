import numpy as np
import pandas as pd
import xgboost as xgb
import sklearn as skl
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field
from backend.models import Soul, ResearchStep, ChatHistory
from backend.tools.data_tool import DataTool
from backend.tools.file_tool import read_file, write_file
from backend.tools.result_tool import map_content_to_frontend
from sqlmodel import Session, select
from textwrap import dedent
import os
import tempfile
import copy
import zipfile
import shutil
import asyncio
import json

from fastapi import UploadFile
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from mcp.shared.exceptions import McpError
import logging

from openai import AsyncOpenAI, AsyncAzureOpenAI

logger = logging.getLogger(__name__)

def run_data_query_tool(query: str, username: Optional[str] = None) -> str:
    """
    Run a SQL query on the data (DuckDB).
    This tool transforms EPSG:28992 coordinates to WGS84 automatically.
    """
    tool = DataTool(username=username)
    return str(tool.execute_query(query))

def read_file_tool(filepath: str) -> str:
    """Read a file."""
    return read_file(filepath)

def write_file_tool(filepath: str, content: str) -> str:
    """Write to a file."""
    return write_file(filepath, content)

@dataclass
class AgentDeps:
    user_soul: Soul
    db_session: Session
    user_id: int
    mcp_url: Optional[str] = None
    mcp_type: Optional[str] = None
    skill_file: Optional[UploadFile] = None

class AgentResponse(BaseModel):
    answer: str = Field( 
        ...,
        description="Short description of the results or why the request cannot be fulfilled."
    )
    related: List[str] = Field(
        default=None,
        max_length=3,
        description="number of SHORT related follow-up USER questions a USER may ask."
    )
    code: Optional[str] = Field(
        default=None,
        description="Complete, runnable Python script (no backticks) that assigns the final output to `result`."
    )
    disclaimer: Optional[str] = Field(
        default=None,
        description="Short disclaimer about data quality, limitations if applicable and urls of datasets used."
    )

# Setup OpenAI client
if os.environ.get("OPENAI_API_KEY"):
    model_name_env = os.environ.get("OPENAI_MODEL_NAME", "gpt-5.2")
    openai_client = AsyncOpenAI()
    model_name = model_name_env
elif os.environ.get("AZURE_OPENAI_API_KEY"):
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.2")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    openai_client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_version=api_version,
    )
    model_name = deployment_name
else:
    openai_client = None
    model_name = 'test'

dataframes = {}
level = "medior"

SYSTEM_PROMPT = dedent(f"""
    You are an expert Python data scientist talking to a {level} user. Always make sure user questions are specific, ask for information if necessary.
    Return a structured JSON output with fields:
    - answer (keep it concise, don't invent anything, use only Context below).
    - related (2 SHORT related questions)
    - code (A complete, self-contained hardened Python script without comments which produces the requested analysis/visualization. The script must contain variables `rows_used` holding the number of analyzed rows, and `result` holding the final output)
    - disclaimer (A short disclaimer about data quality, limitations if applicable and urls of datasets used - use only Context below)
    Based on the user question and chat history.

    ### Context
    - You have access to {len(dataframes)} pre-loaded (geo)pandas (Geo)DataFrames.
    - Access them via the dictionary: dataframes['/datasets/subdir/name.csv']. Non-geometry columns may contain missing values, the hardened code should handle this.
    - All GeoDataFrames are in EPSG:4326 (WGS84). Never modify geometry CRS.
    - You may use ONLY the Python Standard Library and provided global variables: np, pd, px, go, fo, gpd, dataframes, sklearn, xgb


    ### Directives for the `code` field
    1. Stateless Execution: Each request is isolated. Write a complete, self-contained final Python script without comments.
    2. Case-Insensitive Comparisons: When performing string comparisons (e.g., in filters or groupings), always convert text to lowercase.
    3. When you group by year, you use ticks of 1 year in charts.
    4. For Map Visualizations: Use folium (fo) for any geospatial visualizations. Ensure maps are clear and informative. Always use folium.GeoJson(geodataframe). Do not add fo.TileLayer and fo.LayerControl to the map as they are added externally.
    5. Final Output: The result of your script MUST be assigned to a variable named `result`.

    ### Output Requirements for `result` variable
    1. Allowed Types:
        - folium.Map
        - plotly.graph_objects.Figure
        - pandas.DataFrame
        - {{'type': 'download', 'data': bytes, 'filename': str, 'mime': str, 'label': str}}
        - str
    2. Prioritize visualizing results as a folium.Map or plotly.graph_objects.Figure. If neither is possible, use a pandas.DataFrame or str, in that order.
    3. Visualization Style:
        - Folium: use a high-contrast color for geometry and light colors for the map. Zoomlevel should show all geometries.
        - Plotly: default theme with clear titles and axis labels.
    4. The `code` string must contain only raw Python code (with `result` variable), no surrounding backticks or markdown.
    If no code is needed, set `code` to null and provide an explanation in `answer`.
""")

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "data_query",
            "description": "Run a SQL query on the data using DuckDB. Use __PARQUET_DIR__ as a path to access the user's parquet files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to run"
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_content",
            "description": "Read the content of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The path to the file"
                    }
                },
                "required": ["filepath"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file_content",
            "description": "Write content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The path to the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write"
                    }
                },
                "required": ["filepath", "content"],
                "additionalProperties": False
            }
        }
    }
]

def add_soul_context(soul: Soul) -> str:
    return f"User Preferences: {soul.preferences}. Communication Style: {soul.style}."

async def execute_tool(tool_call, deps: AgentDeps, mcp_session: Optional[ClientSession] = None, mcp_name_mapping: Optional[dict] = None) -> str:
    name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return "Error: Invalid JSON arguments provided."

    if name == "data_query":
        return await asyncio.to_thread(run_data_query_tool, args.get("query", ""), username=deps.user_soul.username)
    elif name == "read_file_content":
        return await asyncio.to_thread(read_file_tool, args.get("filepath", ""))
    elif name == "write_file_content":
        return await asyncio.to_thread(write_file_tool, args.get("filepath", ""), args.get("content", ""))
    elif mcp_session and mcp_name_mapping and name in mcp_name_mapping:
        original_name = mcp_name_mapping[name]
        try:
            result = await mcp_session.call_tool(original_name, args)
            return str(result.content)
        except Exception as e:
            return f"Error executing MCP tool {original_name}: {str(e)}"

    return f"Error: Tool {name} not found."

def convert_mcp_tools_to_openai(mcp_tools: list) -> tuple[list, dict]:
    openai_mcp_tools = []
    name_mapping = {}
    for tool in mcp_tools:
        # Provide a basic wrapper around MCP tool parameters
        # MCP tool parameters schema is usually JSON Schema already
        props = getattr(tool, "inputSchema", {}) or getattr(tool, "input_schema", {})
        safe_name = tool.name.replace('-', '_')
        name_mapping[safe_name] = tool.name

        openai_mcp_tools.append({
            "type": "function",
            "function": {
                "name": safe_name,
                "description": tool.description or "",
                "parameters": props if props else {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": True
                }
            }
        })
    return openai_mcp_tools, name_mapping

async def _run_agent_loop(query: str, deps: AgentDeps, messages: list, mcp_session: Optional[ClientSession] = None) -> AgentResponse:
    if model_name == 'test' or openai_client is None:
        return AgentResponse(
            answer="This is a test answer from the mock agent.",
            related=["Test related 1?", "Test related 2?"],
            code="result = 'test result'",
            disclaimer="Test disclaimer"
        )

    tools = list(OPENAI_TOOLS)
    mcp_name_mapping = {}
    if mcp_session:
        mcp_tools_list = await mcp_session.list_tools()
        mcp_tools_openai, mcp_name_mapping = convert_mcp_tools_to_openai(mcp_tools_list.tools)
        tools.extend(mcp_tools_openai)

    max_iterations = 10
    for _ in range(max_iterations):
        logger.info(f"Calling OpenAI with {len(messages)} messages...")

        response = await openai_client.beta.chat.completions.parse(
            model=model_name,
            messages=messages,
            tools=tools if tools else None,
            response_format=AgentResponse,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            message_to_append = {
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": choice.message.tool_calls
            }
            messages.append(message_to_append)

            for tool_call in choice.message.tool_calls:
                logger.info(f"Executing tool {tool_call.function.name} with args {tool_call.function.arguments}")
                tool_result = await execute_tool(tool_call, deps, mcp_session, mcp_name_mapping)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
        else:
            if choice.message.parsed:
                return choice.message.parsed
            else:
                # If for some reason parsed is None, try parsing the content directly
                try:
                    return AgentResponse.model_validate_json(choice.message.content)
                except Exception as e:
                    logger.error(f"Failed to parse response: {e}")
                    raise Exception(f"Failed to parse model response: {choice.message.content}")

    raise Exception("Max iterations reached for agent tool execution loop.")

async def _connect_mcp_and_run(query: str, deps: AgentDeps, messages: list) -> AgentResponse:
    if deps.mcp_url and deps.mcp_type == 'SSE':
        async with sse_client(deps.mcp_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as mcp_session:
                await mcp_session.initialize()
                return await _run_agent_loop(query, deps, messages, mcp_session)

    elif deps.mcp_url and deps.mcp_type == 'STDIO':
        cmd_parts = deps.mcp_url.split()
        if not cmd_parts:
            return await _run_agent_loop(query, deps, messages)

        server_params = StdioServerParameters(command=cmd_parts[0], args=cmd_parts[1:])
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as mcp_session:
                await mcp_session.initialize()
                return await _run_agent_loop(query, deps, messages, mcp_session)
    else:
        return await _run_agent_loop(query, deps, messages)

def get_result(exec_globals, allowed_globals):
    result = copy.deepcopy(exec_globals["result"]) if "result" in exec_globals else None

    for key in list(exec_globals.keys()):
        if key not in allowed_globals and not key.startswith("__"):
            del exec_globals[key]

    return result

async def run_agent(query: str, deps: AgentDeps) -> dict:
    """
    Runs the agent and stores the result in the DB.
    Includes memory/chat history.
    """

    logger.debug(deps)

    # Note: Skills via .zip files and pydantic-ai-skills are not supported in this native OpenAI refactor yet.
    if deps.skill_file:
        logger.warning("Skills are currently not supported. Ignoring skill file.")

    # Fetch recent history
    statement = select(ChatHistory).where(ChatHistory.user_id == deps.user_id).order_by(ChatHistory.timestamp.desc()).limit(10)
    history_records = deps.db_session.exec(statement).all()

    # Reverse to chronological order
    history_records: List[ChatHistory] = list(history_records)
    history_records.reverse()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + add_soul_context(deps.user_soul)}
    ]

    for record in history_records:
        if record.role in ["user", "model", "assistant"]:
            role = "assistant" if record.role == "model" else record.role
            messages.append({"role": role, "content": record.content})

    messages.append({"role": "user", "content": query})

    # Run the agent with history and tools
    try:
        agent_response = await _connect_mcp_and_run(query, deps, messages)
        print(agent_response)
    except Exception as e:
        logger.error(f"Error executing agent in run_agent: {e}", exc_info=True)
        raise e

    # Execute the generated Python code
    exec_globals = { "np": np, "pd": pd, "px": px, "go": go, "gpd": gpd, "xgb": xgb, "skl": skl }
    allowed_globals = set(exec_globals.keys())
    
    exec_result = None
    try:
        if agent_response.code:
            print(agent_response.code)
            exec(agent_response.code, exec_globals)

            result = get_result(exec_globals, allowed_globals)
            
            if result is not None:
                exec_result = map_content_to_frontend(result)
                print(exec_result);
            else:
                exec_result = {"type": "error", "content": "Agent code executed but did not set the 'result' variable."}
        else:
            exec_result = {
                "type" : "answer", 
                "content": { 
                    "answer" : agent_response.answer,
                    "releated": agent_response.related,
                    "disclaimer": agent_response.disclaimer,
                    "code": agent_response.code
                }        
            }
    except Exception as e:
        logger.error(f"Execution error of generated agent code: {e}", exc_info=True)
        exec_result = {"type": "error", "content": f"Execution error: {str(e)}"}

    logger.debug(exec_result)

    model_name_str = str(model_name)

    step = ResearchStep(
        user_id=deps.user_id,
        query=query,
        thought_process="[Agent Execution]",
        output_summary=str(exec_result),
        output_metadata={"model": model_name_str}
    )

    deps.db_session.add(step)
    deps.db_session.commit()

    return {
        "response": {
            "answer" : agent_response.answer,
            "releated": agent_response.related,
            "disclaimer": agent_response.disclaimer,
            "code": agent_response.code
        },
        "exec_result": exec_result
    }
