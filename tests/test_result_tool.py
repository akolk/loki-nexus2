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

def test_map_content_to_frontend_geodataframe_no_crs():
    # Create a GeoDataFrame without explicit CRS
    df = pd.DataFrame(
        {'City': ['Amersfoort'],
         'x': [155000],
         'y': [463000]}
    )
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.x, df.y)
    )

    assert gdf.crs is None

    result = map_content_to_frontend(gdf)

    # It should serialize to geojson_map and transform correctly
    assert result["type"] == "geojson_map"

    features = result["content"]["features"]
    assert len(features) == 1

    # Check that coordinates are transformed to WGS84
    coords = features[0]["geometry"]["coordinates"]
    assert coords[0] == pytest.approx(5.387, abs=0.01)
    assert coords[1] == pytest.approx(52.155, abs=0.01)
