import os
import logging
from typing import Optional
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import NullPool
from sqlalchemy import text

logger = logging.getLogger(__name__)

LOKI_METADATA_HOST = os.environ.get("LOKI_METADATA_HOST", "localhost")
LOKI_METADATA_PORT = os.environ.get("LOKI_METADATA_PORT", "5433")
LOKI_METADATA_DB = os.environ.get("LOKI_METADATA_DB", "loki_metadata")
LOKI_METADATA_USER = os.environ.get("LOKI_METADATA_USER", "postgres")
LOKI_METADATA_PASSWORD = os.environ.get("LOKI_METADATA_PASSWORD", "postgres")

METADATA_DATABASE_URL = f"postgresql+asyncpg://{LOKI_METADATA_USER}:{LOKI_METADATA_PASSWORD}@{LOKI_METADATA_HOST}:{LOKI_METADATA_PORT}/{LOKI_METADATA_DB}"
METADATA_DATABASE_URL_SYNC = f"postgresql://{LOKI_METADATA_USER}:{LOKI_METADATA_PASSWORD}@{LOKI_METADATA_HOST}:{LOKI_METADATA_PORT}/{LOKI_METADATA_DB}"


metadata_engine = create_engine(
    METADATA_DATABASE_URL_SYNC,
    poolclass=NullPool,
    echo=False
)


def get_metadata_session() -> Session:
    return Session(metadata_engine)


async def init_metadata_db():
    create_metadata_tables()


def create_metadata_tables():
    from backend.models_metadata import MetadataSource, MetadataEndpoint, Job, JobRun
    
    try:
        with metadata_engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            SQLModel.metadata.create_all(bind=conn)
        
        logger.info("Metadata tables created successfully.")
    except Exception as e:
        import traceback
        logger.error(f"Error creating metadata tables: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
