import copy
import logging
import os
import shutil
import tempfile
import zipfile
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
import sklearn as skl
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai_skills import SkillsDirectory, SkillsToolset
from sqlmodel import select
from textwrap import dedent

from backend.agents.base import AgentDeps, AgentResponse
from backend.models import ChatHistory, ResearchStep
from backend.tools.file_tool import read_file, write_file
from backend.tools.result_tool import map_content_to_frontend

logger = logging.getLogger(__name__)


if os.environ.get("OPENAI_API_KEY"):
    model_name_env = os.environ.get("OPENAI_MODEL_NAME", "gpt-5.2")
    model = OpenAIResponsesModel(model_name_env)
elif os.environ.get("AZURE_OPENAI_API_KEY"):
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.2")
    model = OpenAIResponsesModel(deployment_name)
else:
    model = None

model_settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort=os.environ.get("OPENAI_REASONING_EFFORT", "low"),
    openai_reasoning_summary=os.environ.get("OPENAI_REASONING_SUMMARY", "auto"),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "50000")),
    model_config={
        "max_retries": int(os.environ.get("OPENAI_MAX_RETRIES", "3"))
    }
) if model else None

level = "medior"


def sys_prompt() -> str:
    return dedent(f"""
        You are an expert Python data scientist talking to a {level} user. Always make sure user questions are specific, ask for information if necessary.
        Return a Pydantic object with fields:
        - answer (keep it concise, don't invent anything, use only Context below).
        - related (2 SHORT related questions)
        - code (A complete, self-contained hardened Python script without comments which produces the requested analysis/visualization. The script must contain variables `rows_used` holding the number of analyzed rows, and `result` holding the final output)
        - disclaimer (A short disclaimer about data quality, limitations if applicable and urls of datasets used - use only Context below)
        Based on the user question and chat history.

        ### Context
        - You may access the internet for OGC APIs or CBS APIs returned by the tools.
        - Calculations must be performed in EPSG:28992 (RD New) and visualizations must be returned in WGS84 (EPSG:4326).
        - You may use ONLY the Python Standard Library and provided global variables: np, pd, px, go, gpd, dataframes, sklearn, xgb

        ### Directives for the `code` field
        1. Stateless Execution: Each request is isolated. Write a complete, self-contained final Python script without comments.
        2. Case-Insensitive Comparisons: When performing string comparisons (e.g., in filters or groupings), always convert text to lowercase.
        3. When you group by year, you use ticks of 1 year in charts.
        4. For Map Visualizations: Return a `geopandas.GeoDataFrame`. It will be rendered on the Leaflet map automatically. Ensure all returned geospatial data is in EPSG:4326.
        5. For Graphs Visualizations: Return a `plotly.graph_objects.Figure`. It will be converted to json and transferred to the frontend.
        5. Final Output: The result of your script MUST be assigned to a variable named `result`.

        ### Output Requirements for `result` variable
        1. Allowed Types:
            - geopandas.GeoDataFrame
            - plotly.graph_objects.Figure
            - pandas.DataFrame
            - {{'type': 'download', 'data': bytes, 'filename': str, 'mime': str, 'label': str}}
            - str
        2. Prioritize visualizing results as a geopandas.GeoDataFrame or plotly.graph_objects.Figure. If neither is possible, use a pandas.DataFrame or str, in that order.
        3. Visualization Style:
            - Plotly: default theme with clear titles and axis labels.
        4. The `code` string must contain only raw Python code (with `result` variable), no surrounding backticks or markdown.
        If no code is needed, set `code` to null and provide an explanation in `answer`.
    """)


agent = Agent(
    model,
    deps_type=AgentDeps,
    output_type=AgentResponse,
    model_settings=model_settings
)


@agent.tool
def pdok_ogc_api(ctx: RunContext[AgentDeps], ogc_dataset: str, top_k: int = 5, filter_geojson: bool = True) -> str:
    """Query the metadata database for the best matching PDOK OGC API endpoints.
    
    Args:
        ogc_dataset: The search query for PDOK datasets
        top_k: Number of results to return (default 5, max 20)
        filter_geojson: If True (default), only return GeoJSON-capable endpoints (OGC API Features with /collections)
    """
    from backend.tools.metadata_lookup import find_endpoint
    top_k = min(max(1, top_k), 20)
    logger.info(f"PDOK_OGC_API: {ogc_dataset}, top_k={top_k}, filter_geojson={filter_geojson}")
    return find_endpoint(ogc_dataset, source_type="pdok", top_k=top_k, filter_geojson=filter_geojson)


@agent.tool
def cbs_api(ctx: RunContext[AgentDeps], cbs_dataset: str, top_k: int = 5) -> str:
    """Query the metadata database for the best matching CBS API endpoints.
    
    Args:
        cbs_dataset: The search query for CBS datasets
        top_k: Number of results to return (default 5, max 20)
    """
    from backend.tools.metadata_lookup import find_endpoint
    top_k = min(max(1, top_k), 20)
    logger.info(f"CBS_API: {cbs_dataset}, top_k={top_k}")
    return find_endpoint(cbs_dataset, source_type="cbs", top_k=top_k)


@agent.tool
def read_file_content(ctx: RunContext[AgentDeps], filepath: str) -> str:
    """Read the content of a file."""
    return read_file(filepath)


@agent.tool
def write_file_content(ctx: RunContext[AgentDeps], filepath: str, content: str) -> str:
    """Write content to a file."""
    return write_file(filepath, content)


@agent.system_prompt
def add_soul_context(ctx: RunContext[AgentDeps]) -> str:
    soul = ctx.deps.user_soul
    return f"User Preferences: {soul.preferences}. Communication Style: {soul.style}."


def get_result(exec_globals: Dict[str, Any], allowed_globals: set) -> Any:
    result = exec_globals.get("result")

    keys_to_delete = exec_globals.keys() - allowed_globals
    for key in keys_to_delete:
        if not key.startswith("__"):
            del exec_globals[key]

    return result


async def run_agent(query: str, deps: AgentDeps) -> Dict[str, Any]:
    """Runs the agent and stores the result in the DB."""
    toolsets: List[Any] = []
    tmp_dir: Optional[str] = None

    logger.debug(deps)

    if deps.skill_file:
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, "skills.zip")
        with open(zip_path, "wb") as f:
            f.write(deps.skill_file)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)

            skills_dir = SkillsDirectory(tmp_dir)
            skill_toolset = SkillsToolset(skills_dir)
            toolsets.append(skill_toolset)
        except Exception as e:
            logger.error(f"Failed to load skills: {e}")

    statement = select(ChatHistory).where(ChatHistory.user_id == deps.user_id).order_by(ChatHistory.timestamp.desc()).limit(10)
    history_records = deps.db_session.exec(statement).all()
    history_records = list(history_records)[::-1]

    message_history: List[ModelMessage] = []

    for record in history_records:
        if record.role == "user":
            message_history.append(ModelRequest(parts=[UserPromptPart(content=record.content)]))
        elif record.role == "model":
            message_history.append(ModelResponse(parts=[TextPart(content=record.content)]))

    try:
        logger.info(message_history)
        logger.info(query)
        result = await agent.run(query, deps=deps, message_history=message_history, toolsets=toolsets, instructions=sys_prompt())
        agent_response = result.output
        logger.debug(f"agent_response={agent_response}")
    except Exception as e:
        logger.error(f"Error executing agent in run_agent: {e}", exc_info=True)
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise e

    if tmp_dir:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    exec_globals = {"np": np, "pd": pd, "px": px, "go": go, "gpd": gpd, "xgb": xgb, "skl": skl}
    allowed_globals = set(exec_globals.keys())

    exec_result: Optional[Dict[str, Any]] = None
    exec_error: Optional[str] = None
    max_retries = 2
    retry_count = 0

    while retry_count <= max_retries:
        try:
            if agent_response.code:
                logger.debug(f"Executing generated code:\n{agent_response.code}")
                exec(agent_response.code, exec_globals)

                result = get_result(exec_globals, allowed_globals)

                if result is not None:
                    exec_result = map_content_to_frontend(result)
                    logger.debug(f"exec_result={exec_result}")
                else:
                    exec_result = {"type": "error", "content": "Agent code executed but did not set the 'result' variable."}
            else:
                exec_result = {
                    "type": "answer",
                    "content": {
                        "answer": agent_response.answer,
                        "related": agent_response.related or [],
                        "disclaimer": agent_response.disclaimer,
                        "code": agent_response.code
                    }
                }
            break
        except Exception as e:
            logger.error(f"Execution error of generated agent code: {e}", exc_info=True)
            exec_error = str(e)
            
            if retry_count < max_retries:
                retry_count += 1
                logger.info(f"Retrying with error context (attempt {retry_count}/{max_retries})")
                
                error_prompt = f"{query}\n\nHerstel fout: {exec_error}\n\nProbeer de code te corrigeren."
                
                try:
                    result = await agent.run(
                        error_prompt, 
                        deps=deps, 
                        message_history=message_history, 
                        toolsets=toolsets, 
                        instructions=sys_prompt()
                    )
                    agent_response = result.output
                    exec_globals = {"np": np, "pd": pd, "px": px, "go": go, "gpd": gpd, "xgb": xgb, "skl": skl}
                except Exception as retry_error:
                    logger.error(f"Error in retry: {retry_error}")
                    exec_result = {"type": "error", "content": f"Execution error: {exec_error}"}
                    break
            else:
                exec_result = {"type": "error", "content": f"Execution error: {exec_error}"}

    logger.debug(exec_result)
    model_name_str = str(model) if model else "test"

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
            "answer": agent_response.answer,
            "related": agent_response.related or [],
            "disclaimer": agent_response.disclaimer,
            "code": agent_response.code,
            "error": exec_error
        },
        "exec_result": exec_result
    }
