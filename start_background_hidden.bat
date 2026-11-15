@echo off
cd /d "%~dp0"
start "" pythonw -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd() / 'live-market-terminal')); import uvicorn; uvicorn.run('web_server:app', host='0.0.0.0', port=8000, reload=False, app_dir=str(Path.cwd() / 'live-market-terminal'))"
echo ===================================================
echo Server is running completely in background (Port 8000).
echo You can close VS Code and all windows.
echo Open http://localhost:8000 in your browser.
echo To stop the server at any time, run stop_server.bat.
echo ===================================================
pause
