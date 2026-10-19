@echo off
setlocal
cd /d "%~dp0"

echo =======================================================
echo     TrustNet AI - Scam Message Isolated Setup
echo =======================================================
echo.
echo Setting up isolated scam detection runtime (.venv-scam)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup\install-scam.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] Scam environment setup failed.
    exit /b 1
)

echo Checking scam model artifacts...
if exist "%~dp0exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip" (
    "%~dp0.venv-scam\Scripts\python.exe" "%~dp0scripts\setup\install-scam-model.py" --package "%~dp0exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip"
    if errorlevel 1 (
        echo [ERROR] Scam model installation failed.
        exit /b 1
    )
) else (
    if not exist "%~dp0models\scam_message\artifacts\model.safetensors" (
        echo [ERROR] model.safetensors is missing!
        echo Please copy model.safetensors or place TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip in exports\
        exit /b 1
    )
)

echo Verifying scam model integrity...
"%~dp0.venv-scam\Scripts\python.exe" "%~dp0scripts\checks\verify-scam.py"
if errorlevel 1 (
    echo [ERROR] Verification failed.
    exit /b 1
)

echo.
echo =======================================================
echo  Scam Message Setup Completed Successfully!
echo  To start TrustNet with all services, run: .\start-dev.bat
echo =======================================================
endlocal
