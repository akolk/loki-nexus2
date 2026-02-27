from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from contextlib import asynccontextmanager

from backend.database import engine, init_db
from backend.models import User, Soul, ChatHistory, ResearchStep
from backend.agent import run_agent, AgentDeps
from backend.scheduler import start_scheduler, add_job, scheduler

# Helper to get session
def get_session():
    with Session(engine) as session:
        yield session

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# Request Models
class ChatRequest(BaseModel):
    message: str

class JobRequest(BaseModel):
    query: str
    interval_seconds: int = 3600

@app.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    x_forwarded_user: str = Header("unknown_user", alias="x-forwarded-user"),
    session: Session = Depends(get_session)
):
    # Ensure user exists
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

    deps = AgentDeps(user_soul=soul, db_session=session, user_id=user.id)

    # Store user message
    user_msg = ChatHistory(user_id=user.id, role="user", content=request.message)
    session.add(user_msg)
    session.commit()
    session.refresh(user_msg)

    try:
        # Run agent
        response_text = await run_agent(request.message, deps)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Store model response
    model_msg = ChatHistory(user_id=user.id, role="model", content=response_text)
    session.add(model_msg)
    session.commit()

    return {"response": response_text}

@app.get("/history")
def get_history(
    x_forwarded_user: str = Header("unknown_user", alias="x-forwarded-user"),
    session: Session = Depends(get_session)
):
    statement = select(User).where(User.username == x_forwarded_user)
    user = session.exec(statement).first()

    if not user:
        return []

    statement = select(ChatHistory).where(ChatHistory.user_id == user.id).order_by(ChatHistory.timestamp)
    history = session.exec(statement).all()
    return history

@app.post("/jobs")
def schedule_job(
    job: JobRequest,
    x_forwarded_user: str = Header("unknown_user", alias="x-forwarded-user"),
    session: Session = Depends(get_session)
):
    statement = select(User).where(User.username == x_forwarded_user)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found (interact with chat first)")

    add_job(user.id, job.query, job.interval_seconds)
    return {"status": "Job scheduled"}

# Serve Frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
