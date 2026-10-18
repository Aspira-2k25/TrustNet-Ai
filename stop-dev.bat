@echo off
setlocal
cd /d "%~dp0"
echo Stopping local TrustNet launcher-owned services...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ops\stop-scam.ps1"
if errorlevel 1 exit /b 1
echo Local launcher-owned processes stopped. Docker containers and volumes preserved.
echo Unrelated processes are never killed by port number.
endlocal
