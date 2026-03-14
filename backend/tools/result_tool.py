import geopandas as gpd
import pandas as pd
import json

def _get_polars_df():
    try:
        import polars as pl
        return pl.DataFrame
    except ImportError:
        return ()

def _get_plotly_fig():
    try:
        import plotly.graph_objects as go
        return go.Figure
    except ImportError:
        return ()

def map_content_to_frontend(content):
    print(f"MAP_TO_CONTENT: {type(content)}")
    if isinstance(content, gpd.GeoDataFrame):
        # Convert to WGS84 just in case, typical for Leaflet
        if content.crs and content.crs.to_string() != "EPSG:4326":
            content = content.to_crs("EPSG:4326")

        geojson_str = content.to_json()
        geojson_data = json.loads(geojson_str)
        return {"type": "geojson_map", "content": {"features": geojson_data.get("features", [])}}

    elif isinstance(content, pd.DataFrame):
        html_table = content.to_html(classes="dataframe-table", index=False)
        return {"type": "dataframe", "content": html_table}

    elif isinstance(content, _get_polars_df()):
        # Convert Polars to Pandas to reuse to_html
        html_table = content.to_pandas().to_html(classes="dataframe-table", index=False)
        return {"type": "dataframe", "content": html_table}

    elif isinstance(content, _get_plotly_fig()):
        return {"type": "plotly", "content": content.to_json()}

    elif isinstance(content, dict):
        if content.get("type") in ["geojson_map", "dataframe", "picture", "html", "plotly", "dict"]:
            return content
        return {"type": content.get("type"), "content": content}

    else:
        return {"type": "error", "content": f"Error: unknown datatype {type(content)}."}
