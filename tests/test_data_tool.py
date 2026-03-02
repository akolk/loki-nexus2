import pytest
from backend.tools.data_tool import DataTool, run_data_query
import duckdb

def test_execute_query_with_limit():
    tool = DataTool()
    tool.con.execute("CREATE TABLE test_limit (id INTEGER)")
    # Insert 200 rows
    tool.con.execute("INSERT INTO test_limit SELECT * FROM range(200)")

    # Query without explicit LIMIT, should be auto-limited to 100
    results = tool.execute_query("SELECT * FROM test_limit")
    assert len(results) == 100

    # Query with explicit LIMIT 50
    results_50 = tool.execute_query("SELECT * FROM test_limit LIMIT 50")
    assert len(results_50) == 50

def test_execute_query_with_rd_coords():
    tool = DataTool()
    tool.con.execute("CREATE TABLE test_coords (id INTEGER, x INTEGER, y INTEGER)")
    tool.con.execute("INSERT INTO test_coords VALUES (1, 155000, 463000)") # Valid RD
    tool.con.execute("INSERT INTO test_coords VALUES (2, -100, 463000)")    # Invalid RD

    results = tool.execute_query("SELECT * FROM test_coords ORDER BY id")
    assert len(results) == 2

    # Row 1 (Valid)
    assert 'wgs84_lon' in results[0]
    assert 'wgs84_lat' in results[0]
    assert 5.0 < results[0]['wgs84_lon'] < 5.5
    assert 52.0 < results[0]['wgs84_lat'] < 52.3

    import math
    # Row 2 (Invalid RD, wgs84 shouldn't be populated for this specific row,
    # but the column exists so it should be NaN)
    assert 'wgs84_lon' in results[1]
    assert math.isnan(results[1]['wgs84_lon'])

def test_execute_query_with_invalid_query():
    tool = DataTool()
    results = tool.execute_query("SELECT * FROM table_that_does_not_exist")
    assert len(results) == 1
    assert "error" in results[0]
    assert "Table with name table_that_does_not_exist does not exist" in results[0]["error"]

def test_run_data_query():
    # Helper wrapper test
    res = run_data_query("SELECT * FROM test_data")
    assert "Test Point" in res
