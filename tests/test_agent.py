import pytest
from backend.agent import read_file_tool, write_file_tool, run_data_query_tool
import os

def test_read_file_tool():
    # Attempt to read a non-existent file
    res = read_file_tool("nonexistent_test_file.txt")
    assert "Error: File nonexistent_test_file.txt not found." in res

def test_write_file_tool():
    res = write_file_tool("test_write.txt", "Hello World")
    assert "File written successfully." in res

    # Read it back
    res = read_file_tool("test_write.txt")
    assert res == "Hello World"

def test_run_data_query_tool():
    res = run_data_query_tool("SELECT 'test' AS a")
    assert "[{'a': 'test'}]" in res
