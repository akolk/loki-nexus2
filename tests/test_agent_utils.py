import pytest
from backend.agents.chat import get_result


def test_get_result_removes_unallowed_globals():
    allowed_globals = {"pd", "np", "px"}

    exec_globals = {
        "pd": "pandas_mock",
        "np": "numpy_mock",
        "px": "plotly_mock",
        "unallowed_var": 123,
        "__builtins__": "builtins_mock",
        "result": "the_final_result",
    }

    res = get_result(exec_globals, allowed_globals)

    # Check if the result variable was returned correctly
    assert res == "the_final_result"

    # Check that allowed globals and dunder globals are kept
    assert "pd" in exec_globals
    assert "np" in exec_globals
    assert "px" in exec_globals
    assert "__builtins__" in exec_globals

    # 'result' is copied out and might not be explicitly deleted but let's check what get_result does.
    # get_result specifically deletes keys NOT in allowed_globals that DO NOT start with "__"
    # "result" is NOT in allowed_globals, so it should be deleted.
    assert "result" not in exec_globals

    # Check that unallowed globals are removed
    assert "unallowed_var" not in exec_globals


def test_get_result_handles_missing_result_key():
    allowed_globals = {"pd"}

    exec_globals = {"pd": "pandas_mock", "temp_var": 456}

    res = get_result(exec_globals, allowed_globals)

    assert res is None
    assert "pd" in exec_globals
    assert "temp_var" not in exec_globals
