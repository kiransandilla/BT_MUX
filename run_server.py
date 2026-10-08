"""Root server runner script for BT-Mux.

Can be run directly from workspace root:
    python run_server.py
"""
import sys
from pathlib import Path
import uvicorn

# Ensure server folder is in sys.path
root_dir = Path(__file__).resolve().parent
server_dir = root_dir / "server"
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        app_dir=str(server_dir),
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
