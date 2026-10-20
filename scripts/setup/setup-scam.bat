@echo off
setlocal
set "TASK_ROOT=%~dp0..\..\"
cd /d "%TASK_ROOT%"

echo =======================================================
echo     TrustNet AI - Scam Message Isolated Setup
echo =======================================================
echo.
echo Setting up isolated scam detection runtime (.venv-scam)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%TASK_ROOT%scripts\setup\install-scam.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] Scam environment setup failed.
    exit /b 1
)

echo Checking scam model artifacts...
if exist "%TASK_ROOT%exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip" (
    "%TASK_ROOT%.venv-scam\Scripts\python.exe" "%TASK_ROOT%scripts\setup\install-scam-model.py" --package "%TASK_ROOT%exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip"
    if errorlevel 1 (
        echo [ERROR] Scam model installation failed.
        exit /b 1
    )
) else (
    if not exist "%TASK_ROOT%models\scam_message\artifacts\model.safetensors" (
        echo [ERROR] model.safetensors is missing!
        echo Please copy model.safetensors or place TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip in exports\
        exit /b 1
    )
)

echo Verifying scam model integrity...
"%TASK_ROOT%.venv-scam\Scripts\python.exe" "%TASK_ROOT%scripts\checks\verify-scam.py"
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
