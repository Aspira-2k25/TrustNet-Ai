@echo off
setlocal
cd /d "%~dp0"
echo TrustNet AI - Full local launcher
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Existing image .venv missing. Restore your image environment first.
    exit /b 1
)
if not exist ".venv-scam\Scripts\python.exe" (
    echo [ERROR] Scam environment missing. Run install-scam.ps1 first.
    exit /b 1
)
if not exist "frontend\node_modules\.bin\vite.cmd" (
    echo [ERROR] Run npm ci in frontend first.
    exit /b 1
)
if "%1"=="--restart" (
    call "%~dp0stop-dev.bat"
)
if "%1"=="-r" (
    call "%~dp0stop-dev.bat"
)
REM Check all ports before launching; never kill unrelated processes.
powershell -NoProfile -Command "$ports = @(8000,8001,8002,8003,8004,8005,5173); $busy = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in $ports }; if ($busy) { Write-Host ('[ERROR] Ports already in use: ' + (($busy.LocalPort | Sort-Object -Unique) -join ', ')); Write-Host '[TIP] Run .\stop-dev.bat to stop existing background services, then re-run start-dev.bat.'; exit 1 }"
if errorlevel 1 exit /b 1
REM Normal synchronous website scans do not require Docker/Kafka.
REM Preserve .env, databases and the original image environment.
set KAFKA_ENABLED=false
set PHISHING_START_ARGS=
set ENABLE_KAFKA_CONSUMER=false
REM Phishing requires Kafka/Mongo; synchronous image/message routes stay available.
docker info >nul 2>&1
if not errorlevel 1 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-phishing-infrastructure.ps1"
    if not errorlevel 1 (
        set KAFKA_ENABLED=true
        set PHISHING_START_ARGS=-PhishingKafka
    )
) else (
    echo [NOTE] Phishing unavailable until Docker Desktop is started.
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-scam.ps1" %PHISHING_START_ARGS%
if errorlevel 1 (
    echo [ERROR] Backend readiness failed. Inspect runtime-logs.
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-web-services.ps1"
if errorlevel 1 (
    echo [ERROR] Website service launch failed. Inspect runtime-logs.
    exit /b 1
)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\check-full-startup.ps1"
if errorlevel 1 exit /b 1
echo Website: http://localhost:5173
echo Startup output is saved in runtime-logs.
echo To stop all services cleanly anytime, run: stop-dev.bat
endlocal

