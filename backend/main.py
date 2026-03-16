from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from backend.database import engine, init_db
from backend.scheduler import (
    start_scheduler,
    start_metadata_scheduler,
    create_metadata_job,
    delete_metadata_job,
    run_metadata_job,
    scheduler
)
from backend.database_metadata import create_metadata_tables
from backend.api import chat_router, jobs_router, metadata_router, user_router

log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_default_metadata_jobs():
    """Create default metadata sync jobs for PDOK and CBS if they don't exist."""
    from backend.database_metadata import get_metadata_session
    from backend.models_metadata import Job
    from sqlmodel import select
    
    session = get_metadata_session()
    try:
        existing_jobs = session.exec(select(Job)).all()
        
        job_names = [j.name for j in existing_jobs]
        
        if "PDOK Metadata Sync" not in job_names:
            create_metadata_job(
                name="PDOK Metadata Sync",
                job_type="METADATA_SYNC",
                schedule_type="INTERVAL",
                config={"source": "pdok"},
                interval_seconds=86400,
                enabled=True
            )
            logger.info("Created default PDOK Metadata Sync job")
        
        if "CBS Metadata Sync" not in job_names:
            create_metadata_job(
                name="CBS Metadata Sync",
                job_type="METADATA_SYNC",
                schedule_type="INTERVAL",
                config={"source": "cbs"},
                interval_seconds=86400,
                enabled=True
            )
            logger.info("Created default CBS Metadata Sync job")
            
    except Exception as e:
        logger.warning(f"Could not create default jobs: {e}")
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    
    try:
        create_metadata_tables()
    except Exception as e:
        logger.warning(f"Could not initialize metadata DB: {e}")
    
    try:
        start_metadata_scheduler()
        
        create_default_metadata_jobs()
    except Exception as e:
        logger.warning(f"Could not start metadata scheduler: {e}")
    
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.include_router(chat_router)
app.include_router(jobs_router)
app.include_router(metadata_router)
app.include_router(user_router)

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
