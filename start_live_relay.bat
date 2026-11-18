@echo off
title Live Market Feed Relay to Railway
echo ===================================================
echo Starting Live Market Feed Relay to Railway Production...
echo Target: https://gemini-agent-production-4247f579.up.railway.app
echo This streams live ticks continuously into your cloud website.
echo ===================================================
cd /d "%~dp0"
python live-market-terminal\scripts\relay_to_railway.py
pause
