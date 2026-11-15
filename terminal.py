"""
Root Launcher for Live Indian Market Terminal CLI.
Delegates directly to live-market-terminal/terminal.py.
"""

import sys
from pathlib import Path

# Insert live-market-terminal into sys.path
TERMINAL_DIR = Path(__file__).resolve().parent / "live-market-terminal"
if str(TERMINAL_DIR) not in sys.path:
    sys.path.insert(0, str(TERMINAL_DIR))

from terminal import main

if __name__ == "__main__":
    main()
