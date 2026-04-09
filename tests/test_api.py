from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import engine, init_db
from sqlmodel import Session, select
from backend.models import User, ChatHistory
import pytest
import os
from unittest.mock import patch, MagicMock

client = TestClient(app)

@patch("backend.api.chat.run_agent")
def test_chat_flow(mock_run_agent):
    mock_run_agent.return_value = {
        "response": {
            "answer": "Mocked Agent Response",
            "related": [],
            "disclaimer": "",
            "code": "",
            "error": "",
            "reasoning": ""
        },
        "exec_result": None
    }

    init_db()

    response = client.post(
        "/chat",
        data={"message": "Hello Agent"},
        headers={"x-forwarded-user": "test_api_user"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "Mocked Agent Response" in data["response"]

    with Session(engine) as session:
        statement = select(User).where(User.username == "test_api_user")
        results = session.exec(statement)
        user = results.first()
        assert user is not None
        assert user.username == "test_api_user"

    response = client.get("/history", headers={"x-forwarded-user": "test_api_user"})
    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 2
    assert history[-2]["content"] == "Hello Agent"
    assert "Mocked Agent Response" in history[-1]["content"]

@patch("backend.api.chat.run_agent")
def test_job_scheduling(mock_run_agent):
    mock_run_agent.return_value = {
        "response": {
            "answer": "ack",
            "related": [],
            "disclaimer": "",
            "code": "",
            "error": "",
            "reasoning": ""
        },
        "exec_result": None
    }
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
