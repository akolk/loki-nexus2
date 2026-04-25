from fastapi import APIRouter, Header
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/info")
def get_user_info(
    x_forwarded_user: str = Header("unknown_user", alias="x-forwarded-user"),
    x_forwarded_groups: str = Header("", alias="x-forwarded-groups"),
) -> Dict[str, Any]:
    """Get current user info."""
    return {
        "username": x_forwarded_user,
        "groups": x_forwarded_groups.split(",") if x_forwarded_groups else [],
    }
