from typing import Dict, Any
from pydantic import BaseModel
from openai import AsyncOpenAI

from backend.agents.base import AgentDeps
from backend.models import ResearchStep

SYSTEM_PROMPT = """
You are an expert Deep Research agent.
Your goal is to perform in-depth data analysis on Parquet data, generate a structured report in the user's requested format.
When your analysis is complete, formulate your final report and return a response containing a summary and the report_path where you saved the file.
Always make sure to do the research comprehensively!
"""


class ResearchResponse(BaseModel):
    summary: str
    report_path: str


async def run_research_agent(query: str, format: str, deps: AgentDeps) -> Dict[str, Any]:
    """Runs the deep research agent and stores the result."""
    from backend.agents.chat import model

    enriched_query = f"Task: {query}\n\nPlease output the final report in the following format: {format}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": enriched_query}
    ]

    client = AsyncOpenAI()
    try:
        completion = await client.beta.chat.completions.parse(
            model=str(model) if model else "test",
            messages=messages,
            response_format=ResearchResponse,
        )
        data = completion.choices[0].message.parsed
    except Exception as e:
        raise e

    model_name_str = str(model) if model else "test"
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
