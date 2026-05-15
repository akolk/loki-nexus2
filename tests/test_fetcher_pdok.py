import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.jobs.fetchers.pdok import fetch_pdok_metadata

@pytest.mark.asyncio
@patch('backend.jobs.fetchers.pdok.httpx.AsyncClient')
@patch('backend.jobs.fetchers.pdok.get_metadata_session')
@patch('backend.jobs.fetchers.pdok.generate_embeddings_batch')
async def test_fetch_pdok_metadata(mock_gen_embeddings, mock_get_session, mock_async_client):
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_session.exec.return_value.first.return_value = MagicMock(id=1)
    mock_session.exec.return_value.all.return_value = []

    mock_client_instance = AsyncMock()
    mock_async_client.return_value.__aenter__.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "apis": [
            {
                "title": "Test API",
                "description": "Test Desc",
                "links": [{"rel": "root", "href": "http://test"}]
            }
        ]
    }

    mock_client_instance.get.return_value = mock_response

    mock_gen_embeddings.return_value = [[0.1] * 1536]

    res = await fetch_pdok_metadata()
    assert "1 added" in res
    assert mock_session.commit.called
