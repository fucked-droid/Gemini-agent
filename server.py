"""
Root Launcher for Live Indian Market Terminal Web Application.
Starts high-performance FastAPI/Uvicorn server with continuous WebSocket broadcasting.
Supports local execution and production cloud deployments (Render, Railway, Docker, Fly.io).
"""

import os
import sys
from pathlib import Path

# Add live-market-terminal to path
TERMINAL_DIR = Path(__file__).resolve().parent / "live-market-terminal"
if str(TERMINAL_DIR) not in sys.path:
    sys.path.insert(0, str(TERMINAL_DIR))

import uvicorn

if __name__ == "__main__":
    # Support cloud port assignment ($PORT) or default to 8000
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print("=" * 70, flush=True)
    print(f"STARTING LIVE INDIAN MARKET WEB TERMINAL (PORT {port})", flush=True)
    print(f"Open http://localhost:{port} in your browser for continuous monitoring.", flush=True)
    print("=" * 70, flush=True)

    uvicorn.run("web_server:app", host=host, port=port, reload=False, app_dir=str(TERMINAL_DIR), log_level="info")
