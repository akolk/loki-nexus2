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

def test_map_content_to_frontend_geodataframe_crs_conversion():
    # Test EPSG:28992 (RD New) to EPSG:4326 (WGS84) conversion
    # Coordinates for Amersfoort in RD New
    df = pd.DataFrame(
        {'City': ['Amersfoort'],
         'x': [155000],
         'y': [463000]}
    )
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.x, df.y), crs="EPSG:28992"
    )

    result = map_content_to_frontend(gdf)

    assert result["type"] == "geojson_map"
    features = result["content"]["features"]
    assert len(features) == 1

    # Amersfoort WGS84 approx lon 5.387, lat 52.155
    coords = features[0]["geometry"]["coordinates"]
    assert coords[0] == pytest.approx(5.387, abs=0.01)
    assert coords[1] == pytest.approx(52.155, abs=0.01)

def test_map_content_to_frontend_geodataframe_drop_id():
    df = pd.DataFrame(
        {'City': ['Amersfoort'],
         'lon': [5.3872],
         'lat': [52.1551]},
        index=[99]
    )
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326"
    )

    result = map_content_to_frontend(gdf)

    assert result["type"] == "geojson_map"
    features = result["content"]["features"]
    assert len(features) == 1
    assert "id" not in features[0]
