import os
import re
import duckdb
import logging
import pandas as pd
import numpy as np
import pyproj
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DataTool:
    """
    Tool for querying data using DuckDB with spatial capabilities.
    Enforces lazy loading/limiting and predicate pushdown.
    """

    def __init__(self, db_path: str = ":memory:", username: Optional[str] = None):
        self.con = duckdb.connect(db_path)
        # Sanitize username: only alphanumeric, underscores, hyphens, and dots
        if username and not re.match(r'^[a-zA-Z0-9._-]+$', username):
            raise ValueError(f"Invalid username: {username}")
        self.username = username
        # Install spatial extension if possible (might not work in all envs without internet/pre-install)
        # We skip this for now as it's complex to setup in sandboxed envs.
        # We rely on pure python projection via pyproj.
        self.transformer = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

    def __del__(self):
        try:
            self.con.close()
        except Exception:
            pass

    def execute_query(self, sql_query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Executes a SQL query and returns a list of dictionaries.
        """
        if self.username:
            parquet_dir = f"/data/{self.username}/"
            # Ensure the directory exists to avoid errors, even if it might be empty
            try:
                os.makedirs(parquet_dir, exist_ok=True)
            except PermissionError:
                logger.warning(f"Could not create {parquet_dir} due to PermissionError")
            sql_query = sql_query.replace("__PARQUET_DIR__", parquet_dir)

        # Enforce limit as integer
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 100

        if not re.search(r'\blimit\b', sql_query, re.IGNORECASE):
            sql_query += f" LIMIT {limit}"

        logger.info(f"Executing query: {sql_query}")

        try:
            # DuckDB executes lazily until fetch
            result = self.con.sql(sql_query)
            # Fetch limited results
            df = result.df() # DuckDB relation -> Pandas DataFrame

            # Transform coordinates if present (EPSG:28992 -> WGS84)
            df = self._transform_coordinates(df)

            # Convert to list of dicts
            data = df.to_dict(orient="records")

            return data
        except Exception as e:
            return [{"error": str(e)}]

    def _transform_coordinates(self, df) -> Any:
        """
        Detects EPSG:28992 (RD New) coordinates and transforms them to WGS84 using Pandas vectorization.
        """
        if 'x' in df.columns and 'y' in df.columns:
            # Simple heuristic check for RD New bounds
            # Ensure x and y are numeric
            x_num = pd.to_numeric(df['x'], errors='coerce')
            y_num = pd.to_numeric(df['y'], errors='coerce')

            mask = (x_num > 0) & (x_num < 300000) & (y_num > 300000) & (y_num < 650000)

            if mask.any():
                # Apply transformation only on valid rows
                # NOTE: EPSG:4326 is lon/lat order when always_xy=True
                # transformer.transform with always_xy=True returns (lon, lat)
                lon, lat = self.transformer.transform(x_num[mask].values, y_num[mask].values)

                # Initialize columns if they don't exist
                if 'wgs84_lon' not in df.columns:
                    df['wgs84_lon'] = np.nan
                if 'wgs84_lat' not in df.columns:
                    df['wgs84_lat'] = np.nan

                df.loc[mask, 'wgs84_lon'] = lon
                df.loc[mask, 'wgs84_lat'] = lat

        return df

# Standalone function for the agent to call
def run_data_query(query: str, username: Optional[str] = None) -> str:
    """
    Runs a DuckDB SQL query.
    Use this tool to analyze large datasets.
    The tool automatically limits results to 100 rows to prevent memory issues.
    If you need aggregations, perform them in the SQL query (predicate pushdown).
    """
    tool = DataTool(username=username)
    # Create a dummy table for testing if not exists
    tool.con.execute("CREATE TABLE IF NOT EXISTS test_data (id INTEGER, x INTEGER, y INTEGER, value VARCHAR)")
    # Insert Amersfoort coordinates (RD New center)
    tool.con.execute("INSERT INTO test_data VALUES (1, 155000, 463000, 'Test Point')")

    results = tool.execute_query(query)
    return str(results)
