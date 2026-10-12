@echo off
setlocal
cd /d "%~dp0"

echo =======================================================
echo          TrustNet AI - Automated Setup Script
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

echo [4/5] Fixing line endings on model artifacts (CRLF to LF)...
powershell -NoProfile -Command "Get-ChildItem -Path '%~dp0models\scam_message\artifacts\*' -File | ForEach-Object { $b = [System.IO.File]::ReadAllBytes($_.FullName); $text = [System.Text.Encoding]::UTF8.GetString($b); if ($text.Contains(\"`r`n\")) { $clean = $text.Replace(\"`r`n\", \"`n\"); [System.IO.File]::WriteAllBytes($_.FullName, [System.Text.Encoding]::UTF8.GetBytes($clean)); Write-Host ('Normalized ' + $_.Name) } }"

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
