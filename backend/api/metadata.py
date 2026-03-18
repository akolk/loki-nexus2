from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import asyncio

from backend.jobs.scheduler import (
    create_job as metadata_create_job,
    delete_job as metadata_delete_job,
    run_job as metadata_run_job
)
from backend.tools.metadata_lookup import search_metadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/skills")
def list_skills() -> Dict[str, Any]:
    """List loaded skills from the skills directory."""
    from backend.skills_manager import get_skills_manager
    
    manager = get_skills_manager()
    if not manager:
        return {"skills_dir": None, "enabled": False, "skills": []}
    
    toolsets = manager.get_toolsets()
    skills = []
    for ts in toolsets:
        prefix = getattr(ts, '_prefix', '')
        skills.append({
            "prefix": prefix,
            "toolset_type": type(ts).__name__
        })
    
    return {
        "skills_dir": manager.skills_dir,
        "enabled": manager._enabled,
        "last_refresh": manager._last_refresh,
        "skills": skills
    }


@router.post("/skills/refresh")
def refresh_skills() -> Dict[str, str]:
    """Force refresh skills from the skills directory."""
    from backend.skills_manager import get_skills_manager
    
    manager = get_skills_manager()
    if not manager:
        raise HTTPException(status_code=404, detail="Skills manager not initialized")
    
    manager.force_refresh()
    return {"status": "Skills refreshed"}


class MetadataJobRequest(BaseModel):
    name: str
    job_type: str = "METADATA_SYNC"
    schedule_type: str = "INTERVAL"
    source: str
    interval_seconds: Optional[int] = 86400
    cron_expression: Optional[str] = None
    enabled: bool = True


@router.post("/jobs")
def create_metadata_job(job_req: MetadataJobRequest) -> Dict[str, Any]:
    try:
        config = {"source": job_req.source}
        
        job = metadata_create_job(
            name=job_req.name,
            job_type=job_req.job_type,
            schedule_type=job_req.schedule_type,
            config=config,
            interval_seconds=job_req.interval_seconds,
            cron_expression=job_req.cron_expression,
            enabled=job_req.enabled
        )
        
        return {
            "status": "Job created",
            "job_id": job.id,
            "name": job.name,
            "schedule_type": job.schedule_type
        }
    except Exception as e:
        logger.error(f"Error creating metadata job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
def list_metadata_jobs() -> List[Dict[str, Any]]:
    from backend.database_metadata import get_metadata_session
    from backend.models_metadata import Job
    from sqlmodel import select
    
    session = get_metadata_session()
    try:
        jobs = session.exec(select(Job)).all()
        return [
            {
                "id": j.id,
                "name": j.name,
                "job_type": j.job_type,
                "schedule_type": j.schedule_type,
                "interval_seconds": j.interval_seconds,
                "cron_expression": j.cron_expression,
                "enabled": j.enabled,
                "last_run": j.last_run.isoformat() if j.last_run else None,
                "next_run": j.next_run.isoformat() if j.next_run else None
            }
            for j in jobs
        ]
    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/jobs/{job_id}")
def delete_metadata_job(job_id: int) -> Dict[str, str]:
    try:
        metadata_delete_job(job_id)
        return {"status": "Job deleted"}
    except Exception as e:
        logger.error(f"Error deleting job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/run")
def run_metadata_job(job_id: int) -> Dict[str, str]:
    try:
        asyncio.run(metadata_run_job(job_id))
        return {"status": "Job completed"}
    except Exception as e:
        logger.error(f"Error running job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
def search_metadata_endpoint(
    q: str,
    source: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    try:
        results = search_metadata(q, source, limit)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
def list_metadata_sources() -> List[Dict[str, Any]]:
    from backend.database_metadata import get_metadata_session
    from backend.models_metadata import MetadataSource
    from sqlmodel import select
    
    session = get_metadata_session()
    try:
        sources = session.exec(select(MetadataSource)).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "base_url": s.base_url,
                "source_type": s.source_type,
                "description": s.description
            }
            for s in sources
        ]
    except Exception as e:
        logger.error(f"Error listing sources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/counts")
def get_metadata_counts() -> Dict[str, Any]:
    """Get endpoint counts for each metadata source."""
    from backend.database_metadata import get_metadata_session
    from backend.models_metadata import MetadataSource, MetadataEndpoint
    from sqlmodel import select, func
    
    session = get_metadata_session()
    try:
        counts = []
        
        sources = session.exec(select(MetadataSource)).all()
        for source in sources:
            count = session.exec(
                select(func.count(MetadataEndpoint.id)).where(MetadataEndpoint.source_id == source.id)
            ).first()
            counts.append({
                "source_id": source.id,
                "source_name": source.name,
                "source_type": source.source_type,
                "endpoint_count": count or 0
            })
        
        return {"sources": counts}
    except Exception as e:
        logger.error(f"Error getting counts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
