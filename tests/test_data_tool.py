import pytest
from backend.tools.data_tool import DataTool, run_data_query
import duckdb
import math

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
    tool.con.execute("INSERT INTO test_coords VALUES (2, -100, 463000)")    # Invalid RD X
    tool.con.execute("INSERT INTO test_coords VALUES (3, 155000, 700000)")  # Invalid RD Y
    tool.con.execute("INSERT INTO test_coords VALUES (4, 400000, 463000)")  # Invalid RD X
    tool.con.execute("INSERT INTO test_coords VALUES (5, 155000, 200000)")  # Invalid RD Y
    tool.con.execute("INSERT INTO test_coords VALUES (6, NULL, NULL)")      # Null RD

    results = tool.execute_query("SELECT * FROM test_coords ORDER BY id")
    assert len(results) == 6

    # Row 1 (Valid)
    assert 'wgs84_lon' in results[0]
    assert 'wgs84_lat' in results[0]
    assert 5.0 < results[0]['wgs84_lon'] < 5.5
    assert 52.0 < results[0]['wgs84_lat'] < 52.3

    # Rows 2-6 (Invalid RD, wgs84 shouldn't be populated for this specific row,
    # but the column exists so it should be NaN)
    for i in range(1, 6):
        assert 'wgs84_lon' in results[i]
        assert math.isnan(results[i]['wgs84_lon'])
        assert math.isnan(results[i]['wgs84_lat'])

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

def test_execute_query_lazy_loading():
    tool = DataTool()
    # Create a dummy table and verify lazy limiting by trying a query that generates more rows than the limit
    tool.con.execute("CREATE TABLE large_table AS SELECT * FROM range(150)")
    results = tool.execute_query("SELECT * FROM large_table")
    # Must enforce lazy limit of 100
    assert len(results) == 100

def test_data_tool_username_directory():
    # When username is provided, query should replace __PARQUET_DIR__
    dt = DataTool(username="john_doe")
    # For testing, we just check if it executed and returned something
    res = dt.execute_query("SELECT '__PARQUET_DIR__' AS path")

    assert res[0]['path'] == "/data/john_doe/"
