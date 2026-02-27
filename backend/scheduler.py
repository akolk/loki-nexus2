import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from backend.agent import run_agent, AgentDeps
from backend.models import User, Soul, ResearchStep
from backend.database import engine, init_db
from sqlmodel import Session, select
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler()

async def scheduled_research_task(user_id: int, query: str):
    """
    A scheduled task that runs the agent for a specific user.
    """
    logger.info(f"Starting scheduled research for user {user_id}: {query}")

    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found.")
            return

        # Reconstruct Soul from user data
        soul = Soul(
            user_id=str(user.id),
            username=user.username,
            preferences=user.soul_data.get("preferences", {}),
            style=user.soul_data.get("style", "concise")
        )

        deps = AgentDeps(user_soul=soul, db_session=session, user_id=user.id)

        try:
            # Run the agent
            result = await run_agent(query, deps)
            logger.info(f"Scheduled task result: {result}")
        except Exception as e:
            logger.error(f"Error in scheduled task: {e}")

def start_scheduler():
    scheduler.start()
    logger.info("Scheduler started.")

def add_job(user_id: int, query: str, interval_seconds: int = 3600):
    scheduler.add_job(
        scheduled_research_task,
        trigger=IntervalTrigger(seconds=interval_seconds),
        args=[user_id, query],
        id=f"research_{user_id}_{hash(query)}",
        replace_existing=True
    )
    logger.info(f"Added job for user {user_id} every {interval_seconds}s")
