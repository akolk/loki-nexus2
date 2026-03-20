import pytest
from unittest.mock import patch
from backend.agent import run_agent, AgentResponse, AgentDeps
from backend.models import Soul
from sqlmodel import Session, create_engine, SQLModel
import asyncio

engine = create_engine("sqlite:///:memory:")
SQLModel.metadata.create_all(engine)

@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session

@pytest.mark.asyncio
async def test_run_agent_execution_with_null_related(db_session):
    soul = Soul(user_id="1", username="test_user", style="concise")
    deps = AgentDeps(user_soul=soul, db_session=db_session, user_id=1)

    mock_agent_response = AgentResponse(
        answer="Answer without related questions.",
        related=None,
        code="result = {'data': 'test_data2', 'type': 'dict'}",
        disclaimer="Mock disclaimer"
    )

    class MockRunResult:
        def __init__(self, output):
            self.output = output

        def all_messages(self):
            return []

    mock_run_result = MockRunResult(mock_agent_response)

    with patch('backend.agents.chat.agent.run', return_value=mock_run_result):
        res = await run_agent("Test no related", deps)

        assert "related" in res["response"]
        assert res["response"]["related"] == []

@pytest.mark.asyncio
async def test_run_agent_execution(db_session):
    # Setup dependencies
    soul = Soul(user_id="1", username="test_user", style="concise")
    deps = AgentDeps(user_soul=soul, db_session=db_session, user_id=1)

    mock_agent_response = AgentResponse(
        answer="Here is the execution result.",
        related=["Q1?"],
        code="result = {'data': 'test_data', 'type': 'dict'}",
        disclaimer="Mock disclaimer"
    )

    class MockRunResult:
        def __init__(self, output):
            self.output = output

        def all_messages(self):
            return []

    mock_run_result = MockRunResult(mock_agent_response)

    with patch('backend.agents.chat.agent.run', return_value=mock_run_result):
        res = await run_agent("Test execution query", deps)

        assert res["exec_result"] is not None
        # `map_content_to_frontend` returns the dict as-is if type is dict
        # wait, let's see what map_content_to_frontend does. It says:
        # if content.get("type") in ["geojson_map", "dataframe", "picture", "html", "plotly", "folium", "dict"]:
        #    return content
        assert res["exec_result"]["data"] == "test_data"
        assert res["response"]["answer"] == "Here is the execution result."
        assert "related" in res["response"]
        assert res["response"]["related"] == ["Q1?"]
