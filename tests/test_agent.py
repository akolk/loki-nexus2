import pytest
from backend.tools.file_tool import read_file, write_file
from backend.tools.data_tool import run_data_query
from backend.agent import AgentDeps
from backend.models import Soul
import os

def test_read_file_tool():
    # Attempt to read a non-existent file
    res = read_file("nonexistent_test_file.txt")
    assert "Error: File nonexistent_test_file.txt not found." in res

def test_write_file_tool():
    res = write_file("test_write.txt", "Hello World")
    assert "File written successfully." in res

    # Read it back
    res = read_file("test_write.txt")
    assert res == "Hello World"

def test_run_data_query_tool():
    res = run_data_query("SELECT 'test' AS a")
    assert "[{'a': 'test'}]" in res

def test_agent_deps_initialization():
    soul = Soul(user_id="1", username="test_user", style="concise")
    deps = AgentDeps(user_soul=soul, db_session=None, user_id=1)

    assert deps.user_soul.username == "test_user"
    assert deps.user_id == 1
    assert deps.mcp_url is None
