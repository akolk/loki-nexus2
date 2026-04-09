import geopandas as gpd
from shapely.geometry import Point
from backend.tools.result_tool import map_content_to_frontend
import json

def test_map_content_to_frontend_geodataframe_missing_crs():
    # Create GeoDataFrame with RD New coordinates but without explicit CRS
    df = gpd.GeoDataFrame(
        {"name": ["Amersfoort"]},
        geometry=[Point(155000, 463000)], # RD New center
        crs=None
    )

    res = map_content_to_frontend(df)

    assert res["type"] == "geojson_map"
    assert "content" in res
    assert "features" in res["content"]

    features = res["content"]["features"]
    assert len(features) == 1

    # Check if the coordinates are transformed to roughly EPSG:4326 (WGS84) for Amersfoort
    # Should be around [5.387..., 52.155...]
    coords = features[0]["geometry"]["coordinates"]
    lon, lat = coords[0], coords[1]

    assert 5.0 < lon < 6.0
    assert 51.0 < lat < 53.0
