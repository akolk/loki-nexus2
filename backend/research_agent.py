from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from backend.agent import AgentDeps, model_name
from backend.models import ResearchStep
import os
import uuid
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class ResearchResponse(BaseModel):
    summary: str
    report_path: str

SYSTEM_PROMPT = """
You are an expert Deep Research agent.
Your goal is to perform in-depth data analysis on Parquet data, generate a structured report in the user's requested format.
When your analysis is complete, formulate your final report and return a response containing a summary and the report_path where you saved the file.
Always make sure to do the research comprehensively!
"""

async def run_research_agent(query: str, format: str, deps: AgentDeps) -> dict:
    """Runs the deep research agent and stores the result."""
    enriched_query = f"Task: {query}\n\nPlease output the final report in the following format: {format}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": enriched_query}
    ]

    client = AsyncOpenAI()
    try:
        completion = await client.beta.chat.completions.parse(
            model=model_name,
            messages=messages,
            response_format=ResearchResponse,
        )
        data = completion.choices[0].message.parsed
    except Exception as e:
        logger.error(f"Error executing research agent: {e}", exc_info=True)
        raise e

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
