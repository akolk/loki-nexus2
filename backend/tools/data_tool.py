import os
import duckdb
from typing import List, Dict, Any, Optional
from pathlib import Path

# Use a persistent database file in the workspace directory
WORKSPACE_DIR = Path("backend/workspace")
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(WORKSPACE_DIR / "agent_data.duckdb")

class DataTool:
    """
    Tool for querying data using DuckDB with spatial capabilities.
    Enforces lazy loading/limiting and predicate pushdown.
    Maintains a persistent file connection.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.con = duckdb.connect(db_path)
        # Spatial extension skipped for standard environments, handled via pyproj

    def execute_query(self, sql_query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Executes a SQL query and returns a list of dictionaries.
        """
        # Inject limit if it looks like a SELECT missing it
        lower_query = sql_query.lower()
        if "select" in lower_query and "limit" not in lower_query:
            sql_query += f" LIMIT {limit}"

        try:
            # DuckDB executes lazily until fetch
            result = self.con.sql(sql_query)

            # If query doesn't return a result (e.g. CREATE TABLE)
            if result is None:
                return [{"status": "Query executed successfully."}]

            # Fetch limited results
            df = result.df() # DuckDB relation -> Pandas DataFrame

            # Convert to list of dicts
            data = df.to_dict(orient="records")

            # Transform coordinates if present (EPSG:28992 -> WGS84)
            data = self._transform_coordinates(data)

            return data
        except Exception as e:
            return [{"error": str(e)}]

    def _transform_coordinates(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detects EPSG:28992 (RD New) coordinates and transforms them to WGS84.
        """
        try:
            import pyproj
            transformer = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
        except ImportError:
            return data # Skip if pyproj not available

        new_data = []
        for row in data:
            new_row = row.copy()
            # Check for RD coordinates (roughly X between 0-300000, Y between 300000-650000)
            if 'x' in row and 'y' in row:
                try:
                    x, y = float(row['x']), float(row['y'])
                    # Simple heuristic check for RD New bounds
                    if 0 < x < 300000 and 300000 < y < 650000:
                        lon, lat = transformer.transform(x, y)
                        new_row['wgs84_lon'] = lon
                        new_row['wgs84_lat'] = lat
                except (ValueError, TypeError):
                    pass
            new_data.append(new_row)
        return new_data

# Global instance so connection is reused within a worker
_global_data_tool = None

def get_data_tool() -> DataTool:
    global _global_data_tool
    if _global_data_tool is None:
        _global_data_tool = DataTool()
    return _global_data_tool

def run_data_query_standalone(query: str) -> str:
    """
    Runs a DuckDB SQL query.
    """
    tool = get_data_tool()
    results = tool.execute_query(query)
    return str(results)
