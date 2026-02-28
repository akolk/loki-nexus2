from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from backend.agent import AgentDeps, model_name
from backend.tools.data_tool import DataTool
from backend.tools.file_tool import write_file, read_file
from backend.models import ResearchStep
import os
import uuid
import duckdb

class ResearchResponse(BaseModel):
    summary: str
    report_path: str

research_agent = Agent(
    model_name,
    deps_type=AgentDeps,
    output_type=ResearchResponse,
    system_prompt=(
        "You are an expert Deep Research agent. "
        "Your goal is to perform in-depth data analysis on Parquet data, generate a structured report in the user's requested format, "
        "and save this report to the workspace using the `write_file_content` tool. "
        "The data is available via the `data_query` tool, which queries DuckDB and handles EPSG:28992 coordinates to WGS84 mapping. "
        "When your analysis is complete, formulate your final report, write it to a file with a suitable extension based on the requested format (e.g. .md, .html), "
        "and return a response containing a summary and the report_path where you saved the file. "
        "Always make sure to do the research comprehensively!"
    )
)

@research_agent.tool
def data_query(ctx: RunContext[AgentDeps], query: str) -> str:
    """Run a SQL query on the data using DuckDB."""
    # Instantiating DataTool with the username
    tool = DataTool(username=ctx.deps.user_soul.username)
    return str(tool.execute_query(query))

@research_agent.tool
def write_file_content(ctx: RunContext[AgentDeps], filepath: str, content: str) -> str:
    """Write content to a file. Ensure the filepath is relative, e.g., 'report.md'"""
    return write_file(filepath, content)

@research_agent.tool
def read_file_content(ctx: RunContext[AgentDeps], filepath: str) -> str:
    """Read content from a file."""
    return read_file(filepath)

async def run_research_agent(query: str, format: str, deps: AgentDeps) -> dict:
    """Runs the deep research agent and stores the result."""
    # Provide the format instructions in the query
    enriched_query = f"Task: {query}\n\nPlease output the final report in the following format: {format}"

    result = await research_agent.run(enriched_query, deps=deps)
    data = result.data

    # Save step to db
    model_name_str = str(model_name)
    step = ResearchStep(
        user_id=deps.user_id,
        query=enriched_query,
        thought_process="[Deep Research Execution]",
        output_summary=f"Report saved to {data.report_path}\nSummary: {data.summary}",
        output_metadata={"model": model_name_str}
    )

    deps.db_session.add(step)
    deps.db_session.commit()

    return {
        "response": f"Deep Research completed.\n\nSummary: {data.summary}\n\nReport saved at: {data.report_path}",
        "exec_result": {
            "type": "html",
            "content": f"<p>Research finished! Check your workspace for <b>{data.report_path}</b></p>"
        }
    }
