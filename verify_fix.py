import sys
import os
from unittest.mock import MagicMock

# Mock duckdb, pandas, pyproj before importing DataTool
sys.modules["duckdb"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["pyproj"] = MagicMock()

import backend.tools.data_tool as data_tool
from backend.tools.data_tool import DataTool


def test_username_sanitization():
    print("Testing username sanitization...")
    safe_usernames = ["user123", "john.doe", "admin_user", "my-name"]
    for u in safe_usernames:
        try:
            DataTool(username=u)
            print(f"  [PASS] Allowed safe username: {u}")
        except ValueError as e:
            print(f"  [FAIL] Rejected safe username: {u} - {e}")
            sys.exit(1)

    malicious_usernames = [
        "'; DROP TABLE users; --",
        "user/../../etc/passwd",
        "admin$(whoami)",
        "user space",
    ]
    for u in malicious_usernames:
        try:
            DataTool(username=u)
            print(f"  [FAIL] Allowed malicious username: {u}")
            sys.exit(1)
        except ValueError as e:
            print(f"  [PASS] Correctly rejected malicious username: {u} - {e}")


def test_limit_enforcement():
    print("\nTesting limit enforcement...")
    # Initialize tool with a safe username to avoid ValueError
    tool = DataTool(username="safe_user")

    # Mock self.con.sql to capture the query
    mock_sql = MagicMock()
    tool.con.sql = mock_sql

    test_cases = [
        (50, "LIMIT 50"),
        ("10", "LIMIT 10"),
        ("invalid; DROP TABLE users; --", "LIMIT 100"),  # should fall back to 100
        (None, "LIMIT 100"),
    ]

    for input_limit, expected_fragment in test_cases:
        # Mock result.df() to return a mock dataframe
        mock_result = MagicMock()
        mock_sql.return_value = mock_result
        mock_df = MagicMock()
        mock_result.df.return_value = mock_df

        # Mock _transform_coordinates
        tool._transform_coordinates = MagicMock(side_effect=lambda x: x)

        mock_sql.reset_mock()
        tool.execute_query("SELECT * FROM test", limit=input_limit)

        # Get the actual query executed
        executed_query = mock_sql.call_args[0][0]
        if expected_fragment in executed_query:
            print(
                f"  [PASS] Input limit '{input_limit}' -> Found '{expected_fragment}' in query"
            )
        else:
            print(
                f"  [FAIL] Input limit '{input_limit}' -> Query: {executed_query} (expected {expected_fragment})"
            )
            sys.exit(1)


if __name__ == "__main__":
    test_username_sanitization()
    test_limit_enforcement()
    print("\nAll security verification tests passed!")
