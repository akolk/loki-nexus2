from backend.tools.file_tool import read_file, write_file
import os

def test_file_tool_sandbox():
    print("Verifying FileTool Sandbox...")

    # Test 1: Write to a valid file
    res = write_file("test.txt", "Hello Sandbox")
    assert "File written successfully" in res, res

    # Test 2: Read from a valid file
    content = read_file("test.txt")
    assert content == "Hello Sandbox", content

    # Test 3: Attempt path traversal (write)
    res = write_file("../hacker.txt", "Bad Content")
    assert "Access denied" in res, f"Expected denial, got: {res}"

    # Test 4: Attempt path traversal (read)
    res = read_file("../../requirements.txt")
    assert "Access denied" in res, f"Expected denial, got: {res}"

    # Test 5: Absolute path outside workspace
    # Note: resolving absolute paths might depend on OS, but we check if it is within WORKSPACE_DIR
    res = read_file("/etc/passwd")
    assert "Access denied" in res or "Error" in res, f"Expected denial/error, got: {res}"

    print("FileTool Sandbox verified.")

if __name__ == "__main__":
    test_file_tool_sandbox()
