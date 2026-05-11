import json
import logging
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db

logging.basicConfig(level=logging.INFO)

# Init db
init_db()

# We can bypass the agent by calling the map_content_to_frontend function directly
# to ensure our backend change in backend/tools/result_tool.py works.

from backend.tools.result_tool import map_content_to_frontend

test_data = {
    "type": "geojson_map",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [5.387, 52.155]},
            "properties": {"name": "Amersfoort"},
        }
    ],
    "tile_servers": [
        {
            "url": "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
            "attribution": "OSM",
        }
    ],
    "answer": "Here is the map you requested.",
}

res = map_content_to_frontend(test_data)
print("Result of map_content_to_frontend:")
print(res)
assert res == test_data
