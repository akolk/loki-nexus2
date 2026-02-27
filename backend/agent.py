from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from backend.models import Soul, ResearchStep, ChatHistory
from backend.tools.data_tool import get_data_tool
from backend.tools.file_tool import read_file, write_file
from sqlmodel import Session, select
from datetime import datetime
import os

# Tools need to be importable functions or classes
def run_data_query_tool(query: str) -> str:
    """
    Run a SQL query on the data (DuckDB).
    This tool transforms EPSG:28992 coordinates to WGS84 automatically.
    """
    tool = get_data_tool()
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

# Use a test model if API key is not present (for CI/build environment)
model_name = 'openai:gpt-4o' if os.environ.get("OPENAI_API_KEY") else 'test'

# Define the agent
agent = Agent(
    model_name,
    deps_type=AgentDeps,
    system_prompt=(
        "You are a helpful data science assistant. "
        "Your goal is to help the user analyze data and answer questions. "
        "You have access to a SQL database (DuckDB) via the `run_data_query` tool. "
        "You can also read and write files in your workspace. "
        "When querying data, always consider performance and use LIMIT clauses if not specified. "
        "If the data contains coordinates in RD (EPSG:28992), they will be automatically transformed to WGS84 by the tool, "
        "so you can focus on the analysis. "
        "Adapt your communication style to the user's preference defined in their Soul."
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


async def run_agent(query: str, deps: AgentDeps) -> str:
    """
    Runs the agent and stores the result in the DB.
    Includes memory/chat history.
    """

    # Load chat history
    statement = select(ChatHistory).where(ChatHistory.user_id == deps.user_id).order_by(ChatHistory.timestamp.desc()).limit(10)
    history_records = deps.db_session.exec(statement).all()

    # Reverse to chronological order
    history_records = list(history_records)
    history_records.reverse()

    message_history: List[ModelMessage] = []

    for record in history_records:
        if record.role == "user":
            message_history.append(ModelRequest(parts=[UserPromptPart(content=record.content)]))
        elif record.role == "model":
            message_history.append(ModelResponse(parts=[TextPart(content=record.content)]))

    # Run the agent with history
    result = await agent.run(query, deps=deps, message_history=message_history)

    # Store the result
    model_name_str = "unknown"
    if hasattr(result, 'model_name'):
        if callable(result.model_name):
            model_name_str = result.model_name()
        else:
            model_name_str = str(result.model_name)

    step = ResearchStep(
        user_id=deps.user_id,
        query=query,
        thought_process="[Agent Execution]",
        output_summary=str(result.data),
        output_metadata={"model": str(model_name_str)}
    )

    deps.db_session.add(step)
    deps.db_session.commit()

    return str(result.data)
