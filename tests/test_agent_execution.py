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

    with patch('backend.agent._connect_mcp_and_run', return_value=mock_agent_response):
        res = await run_agent("Test execution query", deps)

        assert res["exec_result"] is not None
        # `map_content_to_frontend` returns the dict as-is if type is dict
        # wait, let's see what map_content_to_frontend does. It says:
        # if content.get("type") in ["geojson_map", "dataframe", "picture", "html", "plotly", "folium", "dict"]:
        #    return content
        assert res["exec_result"]["data"] == "test_data"
        assert res["response"]["answer"] == "Here is the execution result."

@pytest.mark.asyncio
async def test_execution_isolation(db_session):
    soul = Soul(user_id="1", username="test_user", style="concise")
    deps = AgentDeps(user_soul=soul, db_session=db_session, user_id=1)

    code_to_run = "my_global_var = 42\nresult = {'data': 'isolated', 'type': 'dict'}"

    mock_agent_response = AgentResponse(
        answer="Testing isolation.",
        related=["Q1?"],
        code=code_to_run,
        disclaimer="Mock disclaimer"
    )

    with patch('backend.agent._connect_mcp_and_run', return_value=mock_agent_response):
        res = await run_agent("Test execution isolation query", deps)

        assert res["exec_result"] is not None
        assert res["exec_result"]["data"] == "isolated"

        # Ensure my_global_var did not leak into Python's actual globals
        assert "my_global_var" not in globals()
