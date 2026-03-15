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

def test_map_content_to_frontend_dict_no_type():
    test_dict = {"foo": "bar"}
    result = map_content_to_frontend(test_dict)

    assert result["type"] == "json"
    assert result["content"] == {"foo": "bar"}
