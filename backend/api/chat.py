from fastapi import APIRouter, Depends, Form, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Optional, Dict, Any, Tuple
import json
import logging

from backend.agent import run_agent, AgentDeps
from backend.research_agent import run_research_agent
from backend.models import User, Soul, ChatHistory
from backend.api.dependencies import get_session, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["chat"])


class ResearchRequest(BaseModel):
    query: str
    format: str


class ResearchResponse(BaseModel):
    response: Dict[str, Any]


@router.post("/deep_research")
async def deep_research_endpoint(
    request: ResearchRequest,
    user_data: Tuple[User, Soul] = Depends(get_current_user),
    session = Depends(get_session)
) -> ResearchResponse:
    try:
        user, soul = user_data

        deps = AgentDeps(
            user_soul=soul,
            db_session=session,
            user_id=user.id
        )

        agent_out = await run_research_agent(request.query, request.format, deps)
        return agent_out
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in deep_research_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat_endpoint(
    message: str = Form(...),
    bbox: Optional[str] = Form(None),
    mcp_url: Optional[str] = Form(None),
    mcp_type: Optional[str] = Form(None),
    skill_file: Optional[UploadFile] = File(None),
    user_data: Tuple[User, Soul] = Depends(get_current_user),
    session = Depends(get_session)
) -> Dict[str, Any]:
    try:
        user, soul = user_data

        bbox_dict = None
        if bbox:
            try:
                bbox_dict = json.loads(bbox)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid bbox format")

        deps = AgentDeps(
            user_soul=soul,
            db_session=session,
            user_id=user.id,
            mcp_url=mcp_url,
            mcp_type=mcp_type,
            skill_file=skill_file
        )

        final_message = message
        if bbox_dict:
            bbox_str = f" [Context: Map Viewport BBox: North {bbox_dict.get('north')}, South {bbox_dict.get('south')}, East {bbox_dict.get('east')}, West {bbox_dict.get('west')}]"
            final_message += bbox_str

        user_msg = ChatHistory(user_id=user.id, role="user", content=message)
        session.add(user_msg)
        session.commit()
        session.refresh(user_msg)

        agent_out = await run_agent(final_message, deps)

        response_text = agent_out["response"]["answer"]
        exec_result = agent_out["exec_result"]
        related = agent_out["response"].get("related", [])
        disclaimer = agent_out["response"].get("disclaimer", "Dit antwoord heeft geen disclaimer.")
        code = agent_out["response"].get("code", "Dit antwoord heeft geen code.")
        error = agent_out["response"].get("error", "Geen fouten tijdens ophalen van antwoord.")
        reasoning = agent_out["response"].get("reasoning", None)
        if reasoning:
            logger.info(f"Reasoning: {reasoning}")

        if related:
            related = related[:3]

        model_msg = ChatHistory(user_id=user.id, role="model", content=response_text)
        session.add(model_msg)
        session.commit()

        return {"response": response_text, "exec_result": exec_result, "related": related, "code": code, "disclaimer": disclaimer, "error": error, "reasoning": reasoning}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def get_history(
    x_forwarded_user: str = Header("unknown_user", alias="x-forwarded-user"),
    session = Depends(get_session)
):
    try:
        from sqlmodel import select
        from backend.models import User, ChatHistory
        
        statement = select(User).where(User.username == x_forwarded_user)
        user = session.exec(statement).first()

        if not user:
            return []

        statement = select(ChatHistory).where(ChatHistory.user_id == user.id).order_by(ChatHistory.timestamp)
        history = session.exec(statement).all()
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history")
def delete_history(
    user_data: Tuple[User, Soul] = Depends(get_current_user),
    session = Depends(get_session)
):
    try:
        user, _ = user_data
        from sqlmodel import select
        from backend.models import ChatHistory
        
        statement = select(ChatHistory).where(ChatHistory.user_id == user.id)
        history = session.exec(statement).all()
        for msg in history:
            session.delete(msg)
        session.commit()
        return {"status": "History deleted"}
    except Exception as e:
        logger.error(f"Error in delete_history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
