import pytest
import asyncio
from unittest.mock import patch, MagicMock
from backend.scheduler import scheduled_research_task
from backend.models import User
from sqlmodel import Session, SQLModel, create_engine

# Use an in-memory SQLite database for testing
engine = create_engine("sqlite:///:memory:")
SQLModel.metadata.create_all(engine)

@pytest.fixture
def session():
    with Session(engine) as session:
        yield session

@pytest.mark.asyncio
async def test_scheduled_research_task(session):
    # Setup mock user in the test database
    user = User(username="test_user", soul_data={"style": "concise", "preferences": {}})
    session.add(user)
    session.commit()
    session.refresh(user)

    # Mock dependencies correctly using patch decorators
    with patch("backend.scheduler.engine", engine), \
         patch("backend.scheduler.run_agent") as mock_run_agent:

        # Set mock return value for async agent run
        mock_run_agent.return_value = {"status": "success", "result": "mocked response"}

        # Run the scheduled task
        await scheduled_research_task(user.id, "Test query")

        # Verify run_agent was called with correct arguments
        mock_run_agent.assert_called_once()
        args, kwargs = mock_run_agent.call_args
        assert args[0] == "Test query"

        # Depending on how the patch captured it, 'deps' might be a positional arg
        deps = args[1] if len(args) > 1 else kwargs.get("deps")
        assert deps.user_id == user.id
        assert deps.user_soul.username == "test_user"
