@echo off
title Live Market Terminal Server
echo ===================================================
echo Starting Live Market Terminal Server on port 8000...
echo This window runs independently from VS Code.
echo You can safely close VS Code and the website will stay online!
echo ===================================================
cd /d "%~dp0"
python server.py
pause
