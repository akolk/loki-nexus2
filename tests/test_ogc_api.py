import pytest
from backend.tools.ogc_api import ogc_apis


def test_ogc_apis_loaded():
    assert ogc_apis is not None
    assert isinstance(ogc_apis, list)
    assert len(ogc_apis) > 0
    assert "displaytitle" in ogc_apis[0]
    assert "title" in ogc_apis[0]
    assert "url" in ogc_apis[0]
