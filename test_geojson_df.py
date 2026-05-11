import json
import logging
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db
import geopandas as gpd
from shapely.geometry import Point

logging.basicConfig(level=logging.INFO)

# Init db
init_db()

from backend.tools.result_tool import map_content_to_frontend

df = gpd.GeoDataFrame(
    {"name": ["Amersfoort"]}, geometry=[Point(5.387, 52.155)], crs="EPSG:4326"
)

res = map_content_to_frontend(df)
print("Result of map_content_to_frontend:")
print(res)
assert res["type"] == "geojson_map"
assert "features" in res["content"]
