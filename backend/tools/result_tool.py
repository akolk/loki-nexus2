import geopandas as gpd
import pandas as pd


def map_content_to_frontend(role, content):
    if isinstance(content, (gpd.GeoDataFrame, pd.DataFrame)):
        return { "type": "dataframe", "content": content.to_json(orient='records')}
    elif isinstance(content, dict):
        return { "type": "dict", "content": content }
    else:
        return { "type": "error", "content": {f"Error: unknown datatype {type(content)}."}
