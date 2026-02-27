import os
from pathlib import Path

WORKSPACE_DIR = Path("backend/workspace")
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

def _get_safe_path(filepath: str) -> Path:
    """
    Resolves filepath and ensures it is within the workspace directory.
    Prevents path traversal attacks.
    """
    # Clean the path
    safe_path = (WORKSPACE_DIR / filepath).resolve()

    # Check if the resolved path is within the workspace directory
    if not str(safe_path).startswith(str(WORKSPACE_DIR.resolve())):
        raise ValueError(f"Access denied: {filepath} is outside the workspace.")

    return safe_path

def read_file(filepath: str) -> str:
    """Reads the content of a file from the workspace."""
    try:
        path = _get_safe_path(filepath)
        if not path.exists():
            return f"Error: File {filepath} not found."

        with open(path, 'r') as f:
            return f.read()
    except ValueError as ve:
        return str(ve)
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(filepath: str, content: str) -> str:
    """Writes content to a file in the workspace."""
    try:
        path = _get_safe_path(filepath)
        with open(path, 'w') as f:
            f.write(content)
        return "File written successfully."
    except ValueError as ve:
        return str(ve)
    except Exception as e:
        return f"Error writing file: {e}"
