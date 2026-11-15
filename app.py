"""
Root Launcher for Live Indian Market Terminal Streamlit Dashboard.
Directs Streamlit to execute live-market-terminal/app.py seamlessly.
"""

import sys
from pathlib import Path

# Insert live-market-terminal to path
TERMINAL_DIR = Path(__file__).resolve().parent / "live-market-terminal"
if str(TERMINAL_DIR) not in sys.path:
    sys.path.insert(0, str(TERMINAL_DIR))

# Execute live-market-terminal/app.py code
target_app = TERMINAL_DIR / "app.py"
with open(target_app, encoding="utf-8") as f:
    code = compile(f.read(), str(target_app), "exec")
    exec(code, globals())
