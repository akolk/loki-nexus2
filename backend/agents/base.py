from dataclasses import dataclass
from typing import Optional, List, Union, Any
from pydantic import BaseModel, Field
from sqlmodel import Session

from backend.models import Soul


@dataclass
class AgentDeps:
    user_soul: Soul
    db_session: Session
    user_id: int
    mcp_url: Optional[str] = None
    mcp_type: Optional[str] = None
    skill_files: Any = None


class AgentResponse(BaseModel):
    code: Optional[str] = Field(
        default=None,
        description="Complete, runnable Python script (no backticks) that assigns the final output to `result`.",
    )
    answer: str = Field(
        ...,
        description="Short summary of the results or why the request cannot be fulfilled.",
    )
    related: Optional[List[str]] = Field(
        default=None,
        max_length=3,
        description="number of SHORT related follow-up USER questions a USER may ask.",
    )
    disclaimer: Optional[str] = Field(
        default=None,
        description="Short disclaimer about data quality, limitations if applicable and urls of datasets used.",
    )
    reasoning: Optional[str] = Field(
        default=None, description="LLM reasoning/thinking process if available."
    )
