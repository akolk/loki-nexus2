from backend.tools.data_tool import DataTool
import duckdb

def verify_data_tool():
    print("Verifying DataTool...")
    tool = DataTool()

    # Create test data
    tool.con.execute("CREATE TABLE test (id INTEGER, x INTEGER, y INTEGER)")
    tool.con.execute("INSERT INTO test VALUES (1, 155000, 463000)") # Amersfoort

    # Query data
    results = tool.execute_query("SELECT * FROM test")
    print(f"Results: {results}")

    # Check if transformation happened
    assert len(results) == 1
    assert 'wgs84_lat' in results[0]
    assert 'wgs84_lon' in results[0]

    # Amersfoort (RD: 155000, 463000) is approx (52.155, 5.387) in WGS84
    lat = results[0]['wgs84_lat']
    lon = results[0]['wgs84_lon']
    print(f"Transformed coordinates: Lat {lat}, Lon {lon}")

    assert 52.0 < lat < 52.3
    assert 5.0 < lon < 5.5

    print("DataTool verified.")

if __name__ == "__main__":
    verify_data_tool()
