@echo off
setlocal
cd /d "%~dp0"

echo =======================================================
echo          TrustNet AI - Automated Full Setup Script
echo =======================================================

echo [1/5] Checking Python and Node.js...
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py -3.11
) else (
    set PYTHON_CMD=python
)
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH. Please install Node.js (v18+ or v20+).
    exit /b 1
)

echo [2/5] Setting up main Python environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        python -m venv .venv
    )
)
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Could not create .venv. Ensure Python 3.11 is installed.
    exit /b 1
)
call "%~dp0install-deps.bat"

echo [3/5] Setting up scam detection environment (.venv-scam)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-scam.ps1"
if errorlevel 1 (
    echo [ERROR] Scam environment setup failed.
    exit /b 1
)

echo [4/5] Checking model artifacts...
if not exist "%~dp0models\scam_message\artifacts\model.safetensors" (
    if exist "%~dp0exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip" (
        echo [INFO] model.safetensors missing; extracting from exports ZIP...
        "%~dp0.venv-scam\Scripts\python.exe" "%~dp0install-scam-model.py" --package "%~dp0exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip"
    ) else (
        echo [ERROR] model.safetensors is missing!
        echo Please copy model.safetensors or the complete artifacts folder into:
        echo   models\scam_message\artifacts\
        exit /b 1
    )
)

REM Ensure artifact text files use LF line endings (prevents Windows CRLF checksum error)
powershell -NoProfile -Command "foreach ($f in @('vocab.txt','tokenizer.json','tokenizer_config.json','config.json','special_tokens_map.json')) { $p = Join-Path '%~dp0models\scam_message\artifacts' $f; if (Test-Path $p) { $b = [System.IO.File]::ReadAllBytes($p); $t = [System.Text.Encoding]::UTF8.GetString($b); if ($t.Contains(\"`r`n\")) { [System.IO.File]::WriteAllBytes($p, [System.Text.Encoding]::UTF8.GetBytes($t.Replace(\"`r`n\", \"`n\"))) } } }"

echo [5/5] Installing Frontend dependencies...
cd /d "%~dp0frontend"
call npm install
cd /d "%~dp0"

echo.
echo [VERIFICATION] Verifying model integrity...
"%~dp0.venv-scam\Scripts\python.exe" "%~dp0verify-scam.py"
if errorlevel 1 (
    echo [ERROR] Verification failed. Please check error output above.
    exit /b 1
)

echo.
echo =======================================================
echo  Setup Completed Successfully!
echo  To start the application, run: .\start-dev.bat
echo =======================================================
endlocal
