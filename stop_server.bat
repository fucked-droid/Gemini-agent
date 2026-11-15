@echo off
echo Stopping Live Market Terminal Server on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Terminating PID %%a
    taskkill /F /PID %%a
)
echo Server stopped successfully.
pause
