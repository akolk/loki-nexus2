import os
import duckdb
from typing import List, Dict, Any, Optional

class DataTool:
    """
    Tool for querying data using DuckDB with spatial capabilities.
    Enforces lazy loading/limiting and predicate pushdown.
    """

    def __init__(self, db_path: str = ":memory:", username: Optional[str] = None):
        self.con = duckdb.connect(db_path)
        self.username = username
        # Install spatial extension if possible (might not work in all envs without internet/pre-install)
        # We skip this for now as it's complex to setup in sandboxed envs.
        # We rely on pure python projection via pyproj.

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
            os.makedirs(parquet_dir, exist_ok=True)
            sql_query = sql_query.replace("__PARQUET_DIR__", parquet_dir)

        if "limit" not in sql_query.lower():
            sql_query += f" LIMIT {limit}"

        try:
            # DuckDB executes lazily until fetch
            result = self.con.sql(sql_query)
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
        import pyproj
        transformer = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

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
