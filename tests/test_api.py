from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import engine, init_db
from sqlmodel import Session, select
from backend.models import User, ChatHistory
import pytest
import os
from unittest.mock import patch, MagicMock

# Override dependency or env if needed, but TestClient works well with app
client = TestClient(app)

# Patch the run_agent function to avoid real agent execution/API calls
@patch("backend.main.run_agent")
def test_chat_flow(mock_run_agent):
    # Setup mock
    mock_run_agent.return_value = {"response": "Mocked Agent Response", "exec_result": None}

    # Setup DB
    init_db()

    # 1. Send a chat message
    response = client.post(
        "/chat",
        data={"message": "Hello Agent"},
        headers={"x-forwarded-user": "test_api_user"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "Mocked Agent Response" in data["response"]

    # 2. Verify User creation
    with Session(engine) as session:
        statement = select(User).where(User.username == "test_api_user")
        results = session.exec(statement)
        user = results.first()
        assert user is not None
        assert user.username == "test_api_user"

    # 3. Get history
    response = client.get("/history", headers={"x-forwarded-user": "test_api_user"})
    assert response.status_code == 200
    history = response.json()
    # Should have user message and model response
    assert len(history) >= 2
    assert history[-2]["content"] == "Hello Agent"
    assert "Mocked Agent Response" in history[-1]["content"]

def test_job_scheduling():
    # Ensure user exists first (re-using client state if persistent, but safe to re-init)
    # We need to mock run_agent here too implicitly because /chat calls it
    with patch("backend.main.run_agent") as mock_run:
        mock_run.return_value = {"response": "ack", "exec_result": None}
        client.post(
            "/chat",
            data={"message": "Init user"},
            headers={"x-forwarded-user": "job_user"}
        )

    response = client.post(
        "/jobs",
        json={"query": "Run analysis", "interval_seconds": 3600},
        headers={"x-forwarded-user": "job_user"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Job scheduled"

if __name__ == "__main__":
    test_chat_flow()
    test_job_scheduling()
    print("API Tests Passed.")
