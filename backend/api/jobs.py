from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from backend.scheduler import add_job
from backend.api.dependencies import get_session, get_current_user
from backend.models import User, Soul

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["jobs"])


class JobRequest(BaseModel):
    query: str
    interval_seconds: int = 3600


@router.post("/jobs")
def schedule_job(
    job: JobRequest,
    x_forwarded_user: str = Header("unknown_user", alias="x-forwarded-user"),
    session=Depends(get_session),
) -> Dict[str, str]:
    try:
        from sqlmodel import select

        statement = select(User).where(User.username == x_forwarded_user)
        user = session.exec(statement).first()

        if not user:
            raise HTTPException(
                status_code=404, detail="User not found (interact with chat first)"
            )

        add_job(user.id, job.query, job.interval_seconds)
        return {"status": "Job scheduled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in schedule_job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
