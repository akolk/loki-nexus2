from fastapi import APIRouter

from backend.api.chat import router as chat_router
from backend.api.jobs import router as jobs_router
from backend.api.metadata import router as metadata_router
from backend.api.user import router as user_router

__all__ = ["chat_router", "jobs_router", "metadata_router", "user_router"]
