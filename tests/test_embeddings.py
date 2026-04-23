import sys
import os
from unittest.mock import MagicMock, patch
import pytest

# Mock openai BEFORE importing the module that uses it
mock_openai = MagicMock()
sys.modules["openai"] = mock_openai

import backend.jobs.embeddings

@pytest.fixture(autouse=True)
def reset_openai_client():
    """Reset the global _openai_client before each test."""
    backend.jobs.embeddings._openai_client = None
    mock_openai.AsyncOpenAI.reset_mock()
    yield

def test_get_openai_client_success():
    """Test that get_openai_client returns a client when OPENAI_API_KEY is set."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        client = backend.jobs.embeddings.get_openai_client()
        assert client is not None
        mock_openai.AsyncOpenAI.assert_called_once_with(api_key="test-key")

def test_get_openai_client_missing_key():
    """Test that get_openai_client raises ValueError when OPENAI_API_KEY is missing."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
            backend.jobs.embeddings.get_openai_client()

def test_get_openai_client_singleton():
    """Test that get_openai_client returns the same instance on subsequent calls."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        client1 = backend.jobs.embeddings.get_openai_client()
        client2 = backend.jobs.embeddings.get_openai_client()
        assert client1 is client2
        assert mock_openai.AsyncOpenAI.call_count == 1
