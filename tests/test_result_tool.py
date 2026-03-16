import pytest
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from backend.tools.result_tool import map_content_to_frontend

def test_map_content_to_frontend_geodataframe():
    # Create a simple GeoDataFrame in EPSG:4326
    df = pd.DataFrame(
        {'City': ['Amersfoort'],
         'lon': [5.3872],
         'lat': [52.1551]}
    )
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326"
    )

    result = map_content_to_frontend(gdf)

    # It should serialize to geojson_map
    assert result["type"] == "geojson_map"
    assert "content" in result
    assert "features" in result["content"]

    features = result["content"]["features"]
    assert len(features) == 1

    # Check that coordinates are correctly exported
    coords = features[0]["geometry"]["coordinates"]
    assert coords[0] == pytest.approx(5.3872, abs=0.01)
    assert coords[1] == pytest.approx(52.1551, abs=0.01)

def test_map_content_to_frontend_dataframe():
    df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    result = map_content_to_frontend(df)

    assert result["type"] == "dataframe"
    assert "content" in result
    assert "class=\"dataframe dataframe-table\"" in result["content"]

def test_map_content_to_frontend_dict():
    test_dict = {"type": "html", "content": "<div>Hello</div>"}
    result = map_content_to_frontend(test_dict)

    assert result["type"] == "html"
    assert result["content"] == "<div>Hello</div>"

import unittest.mock
import sys

def test_missing_optional_dependencies():
    # Test fallback behavior when dependencies are missing.
    with unittest.mock.patch.dict('sys.modules', {'polars': None, 'plotly.graph_objects': None}):
        # We need to reload the module to trigger the ImportError logic
        # However, since the module is already imported at the top of the test file,
        # we can just import the logic manually or use importlib.reload.
        import importlib
        import backend.tools.result_tool as result_tool

        # Save original just in case
        original_POLARS_DF_TYPE = result_tool.POLARS_DF_TYPE
        original_PLOTLY_FIG_TYPE = result_tool.PLOTLY_FIG_TYPE

        importlib.reload(result_tool)

        assert result_tool.POLARS_DF_TYPE == ()
        assert result_tool.PLOTLY_FIG_TYPE == ()

        # We can also test the map_content_to_frontend doesn't crash on standard dicts
        # when these types are evaluated as ()
        test_dict = {"type": "dict", "content": "test data"}
        res = result_tool.map_content_to_frontend(test_dict)
        assert res["type"] == "dict"

        # Restore module state
        result_tool.POLARS_DF_TYPE = original_POLARS_DF_TYPE
        result_tool.PLOTLY_FIG_TYPE = original_PLOTLY_FIG_TYPE
