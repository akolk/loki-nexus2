from fastapi import FastAPI, Depends, Header, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel
from contextlib import asynccontextmanager
import json
import logging

from backend.database import engine, init_db
from backend.models import User, Soul, ChatHistory, ResearchStep
from backend.agent import run_agent, AgentDeps
from backend.research_agent import run_research_agent
from backend.scheduler import start_scheduler, add_job, scheduler

logger = logging.getLogger("uvicorn.error")

# Helper to get session
def get_session():
    with Session(engine) as session:
        yield session

def get_current_user(
    x_forwarded_user: str = Header("unknown_user", alias="x-forwarded-user"),
    session: Session = Depends(get_session)
) -> Tuple[User, Soul]:
    statement = select(User).where(User.username == x_forwarded_user)
    results = session.exec(statement)
    user = results.first()

    if not user:
        user = User(username=x_forwarded_user, soul_data={"style": "concise", "preferences": {}})
        session.add(user)
        session.commit()
        session.refresh(user)

    soul = Soul(
        user_id=str(user.id),
        username=user.username,
        preferences=user.soul_data.get("preferences", {}),
        style=user.soul_data.get("style", "concise")
    )
    return user, soul

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# Request Models
class JobRequest(BaseModel):
    query: str
    interval_seconds: int = 3600

class ResearchRequest(BaseModel):
    query: str
    format: str

@app.post("/deep_research")
async def deep_research_endpoint(
    request: ResearchRequest,
    user_data: Tuple[User, Soul] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
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

@app.post("/chat")
async def chat_endpoint(
    message: str = Form(...),
    bbox: Optional[str] = Form(None),
    mcp_url: Optional[str] = Form(None),
    mcp_type: Optional[str] = Form(None),
    skill_file: Optional[UploadFile] = File(None),
    user_data: Tuple[User, Soul] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        user, soul = user_data

        # Parse bbox if provided
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
        print(deps)

        # Enrich prompt with BBox if available
        final_message = message
        if bbox_dict:
            bbox_str = f" [Context: Map Viewport BBox: North {bbox_dict.get('north')}, South {bbox_dict.get('south')}, East {bbox_dict.get('east')}, West {bbox_dict.get('west')}]"
            final_message += bbox_str

        # Store user message (original)
        user_msg = ChatHistory(user_id=user.id, role="user", content=message) # Store clean message for history
        session.add(user_msg)
        session.commit()
        session.refresh(user_msg)

        # Run agent with enriched message
        print(final_message)
        agent_out = await run_agent(final_message, deps)

        response_text = agent_out["response"]
        exec_result = agent_out["exec_result"]

        # Store model response
        model_msg = ChatHistory(user_id=user.id, role="model", content=response_text)
        session.add(model_msg)
        session.commit()

        return {"response": response_text, "exec_result": exec_result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_history(
    x_forwarded_user: str = Header("unknown_user", alias="x-forwarded-user"),
    session: Session = Depends(get_session)
):
    try:
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

@app.post("/jobs")
def schedule_job(
    job: JobRequest,
    x_forwarded_user: str = Header("unknown_user", alias="x-forwarded-user"),
    session: Session = Depends(get_session)
):
    try:
        statement = select(User).where(User.username == x_forwarded_user)
        user = session.exec(statement).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found (interact with chat first)")

        add_job(user.id, job.query, job.interval_seconds)
        return {"status": "Job scheduled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in schedule_job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Serve Frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
