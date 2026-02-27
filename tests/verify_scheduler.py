import asyncio
from backend.scheduler import add_job, start_scheduler, scheduler, scheduled_research_task
from backend.database import init_db, engine
from backend.models import User, ResearchStep, Soul
from sqlmodel import Session
import logging

# Mock run_agent so we don't actually call OpenAI
async def mock_run_agent(query, deps):
    print(f"Mock Agent running query: {query}")
    # In the real flow, the agent writes to DB. Here we do it manually for the test.
    step = ResearchStep(
        user_id=deps.user_id,
        query=query,
        thought_process="Mock thought",
        output_summary="Mock result",
        output_metadata={"mock": True}
    )
    deps.db_session.add(step)
    deps.db_session.commit()
    return "Mock result"

# Monkey patch
import backend.scheduler
backend.scheduler.run_agent = mock_run_agent

async def verify_scheduler():
    logging.basicConfig(level=logging.INFO)
    print("Verifying Scheduler...")
    init_db()

    # Create test user
    with Session(engine) as session:
        # Check if user exists first to avoid unique constraint error on rerun
        user = session.get(User, 1)
        if not user:
            user = User(id=1, username="scheduler_test", soul_data={"style": "concise"})
            session.add(user)
            session.commit()

    # Start scheduler
    start_scheduler()

    # Add a job that runs every 1 second
    add_job(user_id=1, query="Analyze data daily", interval_seconds=1)

    print("Waiting for job to run...")
    await asyncio.sleep(2.5) # Wait for 2 executions approx

    # Check if job ran by inspecting DB
    with Session(engine) as session:
        steps = session.query(ResearchStep).filter(ResearchStep.query == "Analyze data daily").all()
        print(f"Research steps found: {len(steps)}")
        if len(steps) >= 1:
            print("Scheduler verified: Job executed and result stored.")
        else:
            print("Scheduler verification failed: No steps found.")
            exit(1)

    scheduler.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(verify_scheduler())
    except KeyboardInterrupt:
        pass
