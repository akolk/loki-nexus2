import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

from backend.agents import run_agent, AgentDeps
from backend.models import User, Soul
from backend.database import engine
from sqlmodel import Session, select

logger = logging.getLogger(__name__)

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

        soul = Soul(
            user_id=str(user.id),
            username=user.username,
            preferences=user.soul_data.get("preferences", {}),
            style=user.soul_data.get("style", "concise")
        )

        deps = AgentDeps(user_soul=soul, db_session=session, user_id=user.id)

        try:
            result = await run_agent(query, deps)
            logger.info(f"Scheduled task result: {result}")
        except Exception as e:
            logger.error(f"Error in scheduled task: {e}")


def add_job(user_id: int, query: str, interval_seconds: int = 3600) -> None:
    scheduler.add_job(
        scheduled_research_task,
        trigger=IntervalTrigger(seconds=interval_seconds),
        args=[user_id, query],
        id=f"research_{user_id}_{hash(query)}",
        replace_existing=True
    )
    logger.info(f"Added job for user {user_id} every {interval_seconds}s")


def start_scheduler() -> None:
    scheduler.start()
    logger.info("Scheduler started.")


class JobExecutor:
    """Base class for job executors."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def execute(self) -> str:
        raise NotImplementedError("Subclasses must implement execute()")


class MetadataSyncExecutor(JobExecutor):
    """Executor for metadata synchronization jobs."""

    async def execute(self) -> str:
        source = self.config.get("source", "")

        if source == "pdok":
            from backend.jobs.fetchers.pdok import fetch_pdok_metadata
            result = await fetch_pdok_metadata()
        elif source == "cbs":
            from backend.jobs.fetchers.cbs import fetch_cbs_metadata
            result = await fetch_cbs_metadata()
        else:
            result = f"Unknown source: {source}"

        return result


async def run_metadata_job(job_id: int):
    """Execute a metadata job and record the result."""
    from backend.database_metadata import get_metadata_session
    from backend.models_metadata import Job, JobRun

    session = get_metadata_session()

    try:
        job = session.get(Job, job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job_run = JobRun(
            job_id=job_id,
            status="running"
        )
        session.add(job_run)
        session.commit()
        session.refresh(job_run)

        logger.info(f"Starting job {job.name} (ID: {job_id})")

        try:
            executor = get_metadata_executor(job)
            result = await executor.execute()

            job_run.status = "completed"
            job_run.completed_at = datetime.utcnow()
            job_run.result_summary = result

            job.last_run = datetime.utcnow()

        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            job_run.status = "failed"
            job_run.completed_at = datetime.utcnow()
            job_run.error_message = str(e)

        session.commit()

    finally:
        session.close()


def get_metadata_executor(job) -> JobExecutor:
    """Get the appropriate executor for a metadata job."""
    config = job.get_config()

    if job.job_type == "METADATA_SYNC":
        return MetadataSyncExecutor(config)

    raise ValueError(f"Unknown job type: {job.job_type}")


def add_metadata_job_to_scheduler(job):
    """Add or update a metadata job in the APScheduler."""
    job_id = job.id

    if job.schedule_type == "INTERVAL" and job.interval_seconds:
        scheduler.add_job(
            run_metadata_job,
            trigger=IntervalTrigger(seconds=job.interval_seconds),
            args=[job_id],
            id=f"metadata_job_{job_id}",
            replace_existing=True
        )
    elif job.schedule_type == "CRON" and job.cron_expression:
        scheduler.add_job(
            run_metadata_job,
            trigger=CronTrigger.from_crontab(job.cron_expression),
            args=[job_id],
            id=f"metadata_job_{job_id}",
            replace_existing=True
        )
    elif job.schedule_type == "ONCE":
        if job.next_run:
            scheduler.add_job(
                run_metadata_job,
                trigger=DateTrigger(run_date=job.next_run),
                args=[job_id],
                id=f"metadata_job_{job_id}",
                replace_existing=True
            )


def remove_metadata_job_from_scheduler(job_id: int):
    """Remove a metadata job from the APScheduler."""
    try:
        scheduler.remove_job(f"metadata_job_{job_id}")
    except Exception:
        pass


add_job_to_scheduler = add_metadata_job_to_scheduler
remove_job_from_scheduler = remove_metadata_job_from_scheduler


def start_metadata_scheduler():
    """Start the metadata scheduler and load jobs from DB."""
    from backend.database_metadata import get_metadata_session
    from backend.models_metadata import Job

    session = get_metadata_session()

    try:
        jobs = session.exec(select(Job).where(Job.enabled)).all()

        for job in jobs:
            if job.schedule_type != "ONCE":
                add_metadata_job_to_scheduler(job)

        logger.info("Metadata jobs loaded into scheduler.")

    finally:
        session.close()


def create_metadata_job(
    name: str,
    job_type: str,
    schedule_type: str,
    config: Dict[str, Any],
    interval_seconds: Optional[int] = None,
    cron_expression: Optional[str] = None,
    enabled: bool = True
):
    """Create a new metadata job and add it to the scheduler."""
    from backend.database_metadata import get_metadata_session
    from backend.models_metadata import Job

    session = get_metadata_session()

    try:
        job = Job(
            name=name,
            job_type=job_type,
            schedule_type=schedule_type,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            enabled=enabled
        )
        job.set_config(config)

        session.add(job)
        session.commit()
        session.refresh(job)

        if enabled and schedule_type != "ONCE":
            add_metadata_job_to_scheduler(job)

        return job

    finally:
        session.close()


def delete_metadata_job(job_id: int):
    """Delete a metadata job from the scheduler and DB."""
    remove_metadata_job_from_scheduler(job_id)

    from backend.database_metadata import get_metadata_session
    from backend.models_metadata import Job

    session = get_metadata_session()

    try:
        job = session.get(Job, job_id)
        if job:
            session.delete(job)
            session.commit()
    finally:
        session.close()
