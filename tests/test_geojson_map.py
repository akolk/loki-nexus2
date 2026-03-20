import pytest
import geopandas as gpd
from shapely.geometry import Point
from backend.tools.result_tool import map_content_to_frontend

def test_map_content_to_frontend_geodataframe_no_crs():
    # Amersfoort coordinates in RD New (EPSG:28992)
    x, y = 155000, 463000
    df = gpd.GeoDataFrame(
        {"name": ["Amersfoort"]},
        geometry=[Point(x, y)]
    )

    # Assert initial CRS is None
    assert df.crs is None

    # Process through function
    result = map_content_to_frontend(df)

    # Validate structure
    assert result["type"] == "geojson_map"
    assert "features" in result["content"]

    # Extract converted coordinates
    features = result["content"]["features"]
    assert len(features) == 1

    # Converted EPSG:4326 coords (approx: 52.155, 5.387)
    coords = features[0]["geometry"]["coordinates"]
    lon, lat = coords[0], coords[1]

    # WGS84 mapping for Amersfoort
    assert 5.38 < lon < 5.39
    assert 52.15 < lat < 52.16
    assert features[0]["properties"]["name"] == "Amersfoort"
