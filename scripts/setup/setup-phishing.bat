@echo off
setlocal
set "TASK_ROOT=%~dp0..\..\"
cd /d "%TASK_ROOT%"

echo =======================================================
echo     TrustNet AI - Phishing URL Isolated Setup
echo =======================================================
echo.
echo Setting up isolated phishing runtime (.venv-phishing) and model artifacts...
powershell -NoProfile -ExecutionPolicy Bypass -File "%TASK_ROOT%scripts\setup\install-phishing.ps1" %*
if errorlevel 1 (
    echo.
    echo [ERROR] Phishing environment setup failed. See errors above.
    exit /b 1
)

echo.
echo =======================================================
echo  Phishing Setup Completed Successfully!
echo  To start TrustNet with all services, run: .\start-dev.bat
echo =======================================================
endlocal
