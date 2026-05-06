import sys
import os
from unittest.mock import MagicMock, patch
import pytest

import backend.jobs.embeddings

@pytest.fixture(autouse=True)
def reset_openai_client():
    """Reset the global _openai_client before each test."""
    backend.jobs.embeddings._openai_client = None
    yield

@patch("backend.jobs.embeddings.AsyncOpenAI")
def test_get_openai_client_success(mock_async_openai):
    """Test that get_openai_client returns a client when OPENAI_API_KEY is set."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        client = backend.jobs.embeddings.get_openai_client()
        assert client is not None
        mock_async_openai.assert_called_once_with(api_key="test-key")

@patch("backend.jobs.embeddings.AsyncOpenAI")
def test_get_openai_client_missing_key(mock_async_openai):
    """Test that get_openai_client raises ValueError when OPENAI_API_KEY is missing."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
            backend.jobs.embeddings.get_openai_client()

@patch("backend.jobs.embeddings.AsyncOpenAI")
def test_get_openai_client_singleton(mock_async_openai):
    """Test that get_openai_client returns the same instance on subsequent calls."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        client1 = backend.jobs.embeddings.get_openai_client()
        client2 = backend.jobs.embeddings.get_openai_client()
        assert client1 is client2
        assert mock_async_openai.call_count == 1

@pytest.mark.asyncio
@patch("backend.jobs.embeddings.get_openai_client")
async def test_generate_embeddings_batch(mock_get_client):
    """Test generating embeddings for a batch of texts."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_response = MagicMock()

    item1 = MagicMock()
    item1.index = 0
    item1.embedding = [0.1, 0.2, 0.3]

    item2 = MagicMock()
    item2.index = 1
    item2.embedding = [0.4, 0.5, 0.6]

    mock_response.data = [item2, item1]

    # We need to make the create method awaitable
    async def mock_create(*args, **kwargs):
        return mock_response

    mock_client.embeddings.create = mock_create

    texts = ["text1", "text2"]
    embeddings = await backend.jobs.embeddings.generate_embeddings_batch(texts)

    assert len(embeddings) == 2
    assert embeddings[0] == [0.1, 0.2, 0.3]
    assert embeddings[1] == [0.4, 0.5, 0.6]
