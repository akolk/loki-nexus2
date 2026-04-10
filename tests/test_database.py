import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError
from sqlmodel import Session
import time
from backend.database import init_db, get_session

@patch("backend.database.SQLModel.metadata.create_all")
@patch("backend.database.time.sleep")
def test_init_db_success_first_try(mock_sleep, mock_create_all):
    """Test that init_db succeeds on the first try without sleeping."""
    mock_create_all.return_value = None

    init_db()

    mock_create_all.assert_called_once()
    mock_sleep.assert_not_called()

@patch("backend.database.SQLModel.metadata.create_all")
@patch("backend.database.time.sleep")
def test_init_db_success_after_retries(mock_sleep, mock_create_all):
    """Test that init_db succeeds after failing a few times."""
    # Raise OperationalError twice, then succeed
    mock_create_all.side_effect = [
        OperationalError("mock", "mock", "mock"),
        OperationalError("mock", "mock", "mock"),
        None
    ]

    init_db()

    assert mock_create_all.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(2)

@patch("backend.database.SQLModel.metadata.create_all")
@patch("backend.database.time.sleep")
def test_init_db_exhausts_retries(mock_sleep, mock_create_all):
    """Test that init_db exhausts all 10 retries if it continuously fails."""
    # Always raise OperationalError
    mock_create_all.side_effect = OperationalError("mock", "mock", "mock")

    init_db()

    # Should try 10 times and sleep 10 times
    assert mock_create_all.call_count == 10
    assert mock_sleep.call_count == 10
    mock_sleep.assert_called_with(2)

@patch("backend.database.Session")
def test_get_session(mock_session):
    """Test get_session yields a session correctly."""
    mock_session_instance = MagicMock()
    # Mocking the context manager __enter__ to return the instance
    mock_session.return_value.__enter__.return_value = mock_session_instance

    # get_session is a generator
    generator = get_session()

    # Get the yielded session
    session = next(generator)

    assert session is mock_session_instance

    # Complete the generator
    with pytest.raises(StopIteration):
        next(generator)

def test_metadata_db_missing_credentials():
    import importlib
    import os
    import backend.database_metadata

    # Simulate missing credentials
    original_user = os.environ.get("LOKI_METADATA_USER")
    original_password = os.environ.get("LOKI_METADATA_PASSWORD")

    os.environ["LOKI_METADATA_USER"] = ""
    os.environ["LOKI_METADATA_PASSWORD"] = ""

    with pytest.raises(RuntimeError, match="LOKI_METADATA_USER and LOKI_METADATA_PASSWORD environment variables are required."):
        importlib.reload(backend.database_metadata)

    # Restore
    if original_user is not None:
        os.environ["LOKI_METADATA_USER"] = original_user
    else:
        del os.environ["LOKI_METADATA_USER"]

    if original_password is not None:
        os.environ["LOKI_METADATA_PASSWORD"] = original_password
    else:
        del os.environ["LOKI_METADATA_PASSWORD"]

    importlib.reload(backend.database_metadata)
