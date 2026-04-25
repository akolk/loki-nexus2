from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from pgvector.sqlalchemy import Vector
import json


class MetadataSource(SQLModel, table=True):
    __tablename__ = "metadata_source"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    base_url: str = Field(max_length=500)
    source_type: str = Field(max_length=50)  # "pdok" or "cbs"
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MetadataEndpoint(SQLModel, table=True):
    __tablename__ = "metadata_endpoint"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="metadata_source.id")
    endpoint_url: str = Field(max_length=1000)
    title: str = Field(max_length=500)
    description: Optional[str] = None
    api_type: str = Field(max_length=100)  # "OGC API Features", "CBS OData", etc.
    extra_metadata: Optional[str] = Field(default=None)  # JSON string
    embedding: Optional[List[float]] = Field(
        default=None, sa_column=Column(Vector(1536))
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_extra_metadata(self) -> dict:
        if self.extra_metadata:
            return json.loads(self.extra_metadata)
        return {}

    def set_extra_metadata(self, data: dict):
        self.extra_metadata = json.dumps(data)


class Job(SQLModel, table=True):
    __tablename__ = "job"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    job_type: str = Field(max_length=50)  # "METADATA_SYNC"
    schedule_type: str = Field(max_length=50)  # "ONCE", "INTERVAL", "CRON"
    config: Optional[str] = Field(default=None)  # JSON string
    interval_seconds: Optional[int] = None
    cron_expression: Optional[str] = Field(max_length=100, default=None)
    enabled: bool = Field(default=True)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def get_config(self) -> dict:
        if self.config:
            return json.loads(self.config)
        return {}

    def set_config(self, data: dict):
        self.config = json.dumps(data)


class JobRun(SQLModel, table=True):
    __tablename__ = "job_run"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    status: str = Field(max_length=50)  # "running", "completed", "failed"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_summary: Optional[str] = None
