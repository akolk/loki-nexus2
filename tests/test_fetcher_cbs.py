import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.jobs.fetchers.cbs import fetch_cbs_metadata

@pytest.mark.asyncio
@patch('backend.jobs.fetchers.cbs.httpx.AsyncClient')
@patch('backend.jobs.fetchers.cbs.get_metadata_session')
@patch('backend.jobs.fetchers.cbs.generate_embeddings_batch')
async def test_fetch_cbs_metadata(mock_gen_embeddings, mock_get_session, mock_async_client):
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_session.exec.return_value.first.return_value = MagicMock(id=1)
    mock_session.exec.return_value.all.return_value = []

    mock_client_instance = AsyncMock()
    mock_async_client.return_value.__aenter__.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "value": [
            {
                "Identifier": "85025NED",
                "Title": "Test Dataset",
                "Description": "Test Desc",
                "Frequency": "Yearly",
                "Keywords": "test"
            }
        ]
    }
    mock_client_instance.get.return_value = mock_response

    mock_gen_embeddings.return_value = [[0.1] * 1536]

    res = await fetch_cbs_metadata()
    assert "1 added" in res
    assert mock_session.commit.called
