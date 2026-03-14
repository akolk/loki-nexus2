import numpy as np
import pandas as pd
import xgboost as xgb
import sklearn as skl
import geopandas as gpd
import polars as pl
import plotly.express as px
import plotly.graph_objects as go

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from backend.models import Soul, ResearchStep, ChatHistory
from backend.tools.data_tool import DataTool
from backend.tools.file_tool import read_file, write_file
from backend.tools.result_tool import map_content_to_frontend
from backend.tools.ogc_api import ogc_apis
from backend.tools.cbs_api import cbs_apis
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
from pydantic_ai_skills import SkillsToolset, SkillsDirectory
import logging

logger = logging.getLogger(__name__)

# Tools need to be importable functions or classes
# We redefine tool functions here to be used by the agent decorator if needed,
# or use the class methods directly if wrapped.

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


# Use a test model if API key is not present (for CI/build environment)
# Pydantic AI uses `azure:<deployment-name>` for Azure OpenAI
# First check openai, then azure openai
if os.environ.get("OPENAI_API_KEY"):
    model_name_env = os.environ.get("OPENAI_MODEL_NAME", "gpt-5.2")
    model_name = f'openai:{model_name_env}'
elif os.environ.get("AZURE_OPENAI_API_KEY"):
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.2")
    model_name = f'azure:{deployment_name}'
else:
    model_name = 'test'

level = "medior"
dataframes = {}

dfs_info, ogc_info, cbs_info, wfs_info = "", "", "", ""
wfs_apis = {}

for name, df in dataframes.items():
    col_info = ", ".join([f"`{col}` ({dtype})" for col, dtype in df.dtypes.items()])
    dfs_info += f"- {name}: {df.shape[0]} rows, {df.shape[1]} columns\n  - Columns: {col_info}\n"

#metadata = get_relevant_metadata(list(dataframes.keys()))
#metadata_part = f"\nWith metadata:\n  {json.dumps(metadata)}" if metadata else ""
metadata_part = ""


for api in ogc_apis:
    ogc_info += f"         - {api['url']} : {api['title']}\n"
for api in cbs_apis:
    cbs_info += f"         - {api['url']} : {api['displaytitle']}\n"
for api in wfs_apis:
    wfs_info += f"         - {api['url']} : {api['displaytitle']}\n"
    
system_prompt=dedent(f"""
        You are an expert Python data scientist talking to a {level} user. Always make sure user questions are specific, ask for information if necessary.
        Return a Pydantic object with fields:
        - answer (keep it concise, don't invent anything, use only Context below).
        - related (2 SHORT related questions)
        - code (A complete, self-contained hardened Python script without comments which produces the requested analysis/visualization. The script must contain variables `rows_used` holding the number of analyzed rows, and `result` holding the final output)
        - disclaimer (A short disclaimer about data quality, limitations if applicable and urls of datasets used - use only Context below)
        Based on the user question and chat history.

        ### Context
        - You have access to {len(dataframes)} pre-loaded (geo)pandas (Geo)DataFrames.
        - Access them via the dictionary: dataframes['/datasets/subdir/name.csv']. Non-geometry columns may contain missing values, the hardened code should handle this.
        - All GeoDataFrames are in EPSG:4326 (WGS84). Never modify geometry CRS.
        - You may use ONLY the Python Standard Library and provided global variables: np, pd, pl, px, go, gpd, dataframes, sklearn, xgb
        - The available dataframes and their schemas are:
        {dfs_info}{metadata_part}
        {f"- Available OGC APIs are (bbox filter only and use link-based pagination (999)):\n {json.dumps(ogc_apis)}" if ogc_info else ""}
        {f"- Available CBS APIs are (use appropriate RegioS filters and pagination (9999)):\n {json.dumps(cbs_apis)}" if cbs_info else ""}
        {f"- Available WFS APIs are: {wfs_info}" if wfs_info else ""}

        ### Directives for the `code` field
        1. Stateless Execution: Each request is isolated. Write a complete, self-contained final Python script without comments.
        2. Case-Insensitive Comparisons: When performing string comparisons (e.g., in filters or groupings), always convert text to lowercase.
        3. When you group by year, you use ticks of 1 year in charts.
        4. For Map Visualizations: Use geopandas.GeoDataFrame for any geospatial visualizations. Ensure maps are clear and informative.
        5. For Graph Visualizations: Always use plotly.graph_objects.Figure for graphs. Do not use matplotlib or other external libraries.
        6. Final Output: The result of your script MUST be assigned to a variable named `result`.

        ### Output Requirements for `result` variable
        1. Allowed Types:
            - geopandas.GeoDataFrame
            - polars.DataFrame
            - plotly.graph_objects.Figure
            - pandas.DataFrame
            - {{'type': 'download', 'data': bytes, 'filename': str, 'mime': str, 'label': str}}
            - str
        2. Prioritize visualizing results as a geopandas.GeoDataFrame or plotly.graph_objects.Figure. If neither is possible, use a polars.DataFrame, pandas.DataFrame or str, in that order.
        3. Visualization Style:
            - Map (GeoDataFrame): ensure it uses EPSG:4326.
            - Plotly: default theme with clear titles and axis labels.
        4. The `code` string must contain only raw Python code (with `result` variable), no surrounding backticks or markdown.
        If no code is needed, set `code` to null and provide an explanation in `answer`.
    """)

print(f"prompt={system_prompt}")

# Define the agent
agent = Agent(
    model_name,
    deps_type=AgentDeps,
    output_type=AgentResponse,
    system_prompt=system_prompt
)

# Register tools explicitly
@agent.tool
def data_query(ctx: RunContext[AgentDeps], query: str) -> str:
    """
    Run a SQL query on the data using DuckDB.
    Use __PARQUET_DIR__ as a path to access the user's parquet files (e.g. read_parquet('__PARQUET_DIR__*.parquet')).
    """
    return run_data_query_tool(query, username=ctx.deps.user_soul.username)

@agent.tool
def read_file_content(ctx: RunContext[AgentDeps], filepath: str) -> str:
    """Read the content of a file."""
    return read_file_tool(filepath)

@agent.tool
def write_file_content(ctx: RunContext[AgentDeps], filepath: str, content: str) -> str:
    """Write content to a file."""
    return write_file_tool(filepath, content)


@agent.system_prompt
def add_soul_context(ctx: RunContext[AgentDeps]) -> str:
    soul = ctx.deps.user_soul
    return f"User Preferences: {soul.preferences}. Communication Style: {soul.style}."

from pydantic_ai.toolsets import FunctionToolset

def _create_mcp_toolset(mcp_session: ClientSession, tools_list: list) -> FunctionToolset:
    toolset = FunctionToolset()
    for mcp_tool in tools_list:
        async def make_wrapper(name: str):
            async def mcp_tool_wrapper(ctx: RunContext[AgentDeps], **kwargs) -> str:
                result = await mcp_session.call_tool(name, kwargs)
                return str(result.content)
            return mcp_tool_wrapper

        wrapper = asyncio.run(make_wrapper(mcp_tool.name))
        wrapper.__name__ = mcp_tool.name.replace('-', '_') # Ensure valid python function name
        wrapper.__doc__ = mcp_tool.description or ""
        toolset.tool(wrapper)
    return toolset


async def _connect_mcp_and_run(query: str, deps: AgentDeps, message_history: List[ModelMessage], toolsets: list) -> AgentResponse:
    # Helper to connect to MCP and run the agent
    if deps.mcp_url and deps.mcp_type == 'SSE':
        async with sse_client(deps.mcp_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as mcp_session:
                await mcp_session.initialize()

                # Dynamic tools from MCP
                tools = await mcp_session.list_tools()

                mcp_toolset = _create_mcp_toolset(mcp_session, tools.tools)
                run_toolsets = toolsets + [mcp_toolset]

                result = await agent.run(query, deps=deps, message_history=message_history, toolsets=run_toolsets)
                return result.output

    elif deps.mcp_url and deps.mcp_type == 'STDIO':
        # Assuming URL is the command for STDIO
        cmd_parts = deps.mcp_url.split()
        if not cmd_parts:
            # Fallback if command is empty
            result = await agent.run(query, deps=deps, message_history=message_history, toolsets=toolsets)
            return result.output

        server_params = StdioServerParameters(command=cmd_parts[0], args=cmd_parts[1:])
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as mcp_session:
                await mcp_session.initialize()
                tools = await mcp_session.list_tools()

                mcp_toolset = _create_mcp_toolset(mcp_session, tools.tools)
                run_toolsets = toolsets + [mcp_toolset]

                result = await agent.run(query, deps=deps, message_history=message_history, toolsets=run_toolsets)
                return result.output
    else:
        logger.info(query)
        result = await agent.run(query, deps=deps, message_history=message_history, toolsets=toolsets)
        logger.info(result)
        return result.output

async def run_agent(query: str, deps: AgentDeps) -> dict:
    """
    Runs the agent and stores the result in the DB.
    Includes memory/chat history.
    """

    toolsets = []
    tmp_dir = None

    logger.debug(deps)

    # Load skill file if provided
    if deps.skill_file:
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, "skills.zip")
        with open(zip_path, "wb") as f:
            f.write(await deps.skill_file.read())

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)

            # Use pydantic-ai-skills to load from directory
            skills_dir = SkillsDirectory(tmp_dir)
            skill_toolset = SkillsToolset(skills_dir)
            toolsets.append(skill_toolset)
        except Exception as e:
            print(f"Failed to load skills: {e}")

    # Load chat history
    # Pydantic AI uses a list of messages. We need to convert our DB history to Pydantic AI messages.
    # Note: Pydantic AI expects specific message types.

    # Fetch recent history (e.g. last 10 messages) to keep context manageable
    statement = select(ChatHistory).where(ChatHistory.user_id == deps.user_id).order_by(ChatHistory.timestamp.desc()).limit(10)
    history_records = deps.db_session.exec(statement).all()

    # Reverse to chronological order (oldest first)
    # The result of all() on a slice/limit query might be a list, we reverse it.
    history_records: List[ChatHistory] = list(history_records)
    history_records.reverse()

    message_history: List[ModelMessage] = []

    for record in history_records:
        if record.role == "user":
            message_history.append(ModelRequest(parts=[UserPromptPart(content=record.content)]))
        elif record.role == "model":
            # For simplicity, we assume model response is text.
            # In a full system we'd parse tool calls if we stored them.
            message_history.append(ModelResponse(parts=[TextPart(content=record.content)]))

    # Run the agent with history and toolsets
    try:
        agent_response = await _connect_mcp_and_run(query, deps, message_history, toolsets)
        print(agent_response)
    except Exception as e:
        logger.error(f"Error executing agent in run_agent: {e}", exc_info=True)
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise e

    if tmp_dir:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Execute the generated Python code
    exec_env = { "np": np, "pd": pd, "pl": pl, "px": px, "go": go, "gpd": gpd, "xgb": xgb, "skl": skl }
    
    exec_result = None
    try:
        if agent_response.code:
            print(agent_response.code)
            exec(agent_response.code, exec_env)

            result = copy.deepcopy(exec_env.get("result"))
            
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
    # Determine model string for metadata
    model_name_str = str(model_name)

    # Store the result (ResearchStep)
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
