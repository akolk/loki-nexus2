from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from backend.models import Soul, ResearchStep, ChatHistory
from backend.tools.data_tool import DataTool
from backend.tools.file_tool import read_file, write_file
from sqlmodel import Session, select
from datetime import datetime
import os
import tempfile
import zipfile
import shutil
import asyncio

from fastapi import UploadFile
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from mcp.shared.exceptions import McpError
from pydantic_ai_skills import SkillsToolset, SkillsDirectory

# Tools need to be importable functions or classes
# We redefine tool functions here to be used by the agent decorator if needed,
# or use the class methods directly if wrapped.

def run_data_query_tool(query: str) -> str:
    """
    Run a SQL query on the data (DuckDB).
    This tool transforms EPSG:28992 coordinates to WGS84 automatically.
    """
    tool = DataTool()
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
    code: str
    disclaimer: Optional[str]
    followup: List[str]

# Use a test model if API key is not present (for CI/build environment)
model_name = 'openai:gpt-4o' if os.environ.get("OPENAI_API_KEY") else 'test'

# Define the agent
agent = Agent(
    model_name,
    deps_type=AgentDeps,
    output_type=AgentResponse,
    system_prompt=(
        "You are a helpful data science assistant. "
        "Your goal is to help the user analyze data and answer questions by returning executable Python code. "
        "You MUST structure your response according to the defined schema. "
        "The `code` field MUST contain valid Python code. "
        "When your code executes, it MUST define a variable named `result` which is a dictionary containing: "
        "{'type': '...', 'content': '...'}. "
        "Valid types are: 'dataframe', 'picture', 'html', 'plotly', 'folium'. "
        "Do not assume any imports are pre-loaded; import everything you need in the code block. "
        "You have access to a SQL database (DuckDB) via the `run_data_query` tool if you need to inspect data while planning. "
        "You can also read and write files in your workspace. "
        "When querying data, always consider performance and use LIMIT clauses if not specified. "
        "If the data contains coordinates in RD (EPSG:28992), they will be automatically transformed to WGS84 by the tool, "
        "so you can focus on the analysis. "
        "Adapt your communication style to the user's preference defined in their Soul in the `disclaimer` or `followup`."
    )
)

# Register tools explicitly
@agent.tool
def data_query(ctx: RunContext[AgentDeps], query: str) -> str:
    """
    Run a SQL query on the data using DuckDB.
    """
    return run_data_query_tool(query)

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
                return result.data

    elif deps.mcp_url and deps.mcp_type == 'STDIO':
        # Assuming URL is the command for STDIO
        cmd_parts = deps.mcp_url.split()
        if not cmd_parts:
            # Fallback if command is empty
            result = await agent.run(query, deps=deps, message_history=message_history, toolsets=toolsets)
            return result.data

        server_params = StdioServerParameters(command=cmd_parts[0], args=cmd_parts[1:])
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as mcp_session:
                await mcp_session.initialize()
                tools = await mcp_session.list_tools()

                mcp_toolset = _create_mcp_toolset(mcp_session, tools.tools)
                run_toolsets = toolsets + [mcp_toolset]

                result = await agent.run(query, deps=deps, message_history=message_history, toolsets=run_toolsets)
                return result.data
    else:
        result = await agent.run(query, deps=deps, message_history=message_history, toolsets=toolsets)
        return result.data

async def run_agent(query: str, deps: AgentDeps) -> dict:
    """
    Runs the agent and stores the result in the DB.
    Includes memory/chat history.
    """

    toolsets = []
    tmp_dir = None

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
    history_records = list(history_records)
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
    except Exception as e:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise e

    if tmp_dir:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Execute the generated Python code
    env = {}
    try:
        exec(agent_response.code, env)
        exec_result = env.get("result")
        if not exec_result:
            exec_result = {"type": "error", "content": "Agent code executed but did not set the 'result' variable."}
    except Exception as e:
        exec_result = {"type": "error", "content": f"Execution error: {str(e)}"}

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
        "response": f"Disclaimer: {agent_response.disclaimer}\n\nFollowups: {', '.join(agent_response.followup)}",
        "exec_result": exec_result
    }
