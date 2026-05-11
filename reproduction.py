import os
import duckdb
from backend.tools.data_tool import DataTool


def test_sql_injection():
    # Simulate a malicious username
    malicious_username = "'; CREATE TABLE injected (val TEXT); --"
    tool = DataTool(db_path="test.db", username=malicious_username)

    # Query that uses __PARQUET_DIR__
    sql_query = "SELECT * FROM read_parquet('__PARQUET_DIR__*.parquet')"

    print(f"Original query: {sql_query}")
    try:
        # This will probably fail because /data/ exists or not, but let's see if it executes the injected SQL
        tool.execute_query(sql_query)
    except Exception as e:
        print(f"Caught expected exception: {e}")

    # Check if the 'injected' table was created
    con = duckdb.connect("test.db")
    tables = con.execute("SHOW TABLES").fetchall()
    print(f"Tables in DB: {tables}")
    con.close()

    if any("injected" in table for table in tables):
        print("VULNERABILITY REPRODUCED: Table 'injected' was created!")
    else:
        print("Vulnerability not reproduced (or failed for other reasons).")


if __name__ == "__main__":
    if os.path.exists("test.db"):
        os.remove("test.db")
    test_sql_injection()
    if os.path.exists("test.db"):
        os.remove("test.db")
