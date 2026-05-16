import os
import sys
import uvicorn

# This script ensures that the 'app' directory is properly recognized as a package
# by adding the current root directory to the Python path before starting uvicorn.

if __name__ == "__main__":
    # Add the current directory to sys.path
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if root_dir not in sys.path:
        sys.path.append(root_dir)
    
    print(f"Starting SHL Advisor Backend on http://127.0.0.1:8001")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
