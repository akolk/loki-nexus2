from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, JSON
from pydantic import BaseModel

# User & Soul
class Soul(BaseModel):
    """
    Represents the user's soul/context/preferences.
    This is not a DB model, but a Pydantic model used in the agent dependency.
    """
    user_id: str
    username: str
    preferences: Dict[str, Any] = {}
    style: str = "concise"  # e.g. "concise", "detailed", "technical"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Storing soul data as JSON for flexibility
    soul_data: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

# Research Artifacts
class ResearchStep(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query: str
    thought_process: str
    code_generated: Optional[str] = None
    output_summary: str
    output_metadata: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON) # e.g. row_count, execution_time

# Chat History
class ChatHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    role: str # "user" or "model"
    content: str
