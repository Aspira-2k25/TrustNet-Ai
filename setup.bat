@echo off
setlocal
cd /d "%~dp0"

echo =======================================================
echo          TrustNet AI - Project Setup Script
echo =======================================================

REM Handle modular setup arguments
if /i "%1"=="--phishing" goto :setup_phishing_only
if /i "%1"=="phishing"   goto :setup_phishing_only
if /i "%1"=="-p"         goto :setup_phishing_only

if /i "%1"=="--scam"     goto :setup_scam_only
if /i "%1"=="scam"       goto :setup_scam_only
if /i "%1"=="-s"         goto :setup_scam_only

if /i "%1"=="--verify"   goto :verify_all_only
if /i "%1"=="verify"     goto :verify_all_only
if /i "%1"=="-v"         goto :verify_all_only

echo [1/5] Checking Python and Node.js...
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py -3.11
) else (
    set PYTHON_CMD=python
)
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH. Install Node.js 24 LTS.
    exit /b 1
)
%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)"
if errorlevel 1 (
    echo [ERROR] Python 3.11 is required.
    exit /b 1
)
node -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit(a===20&&b>=19||a===22&&b>=12||a>=24?0:1)"
if errorlevel 1 (
    echo [ERROR] Unsupported Node.js version. Install Node.js 24 LTS.
    exit /b 1
)

echo [2/5] Checking main Python environment (.venv)...
set INSTALL_MAIN_DEPS=false
if not exist ".venv\Scripts\python.exe" (
    set INSTALL_MAIN_DEPS=true
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        python -m venv .venv
    )
)
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Could not create .venv. Ensure Python 3.11 is installed.
    exit /b 1
)
if "%INSTALL_MAIN_DEPS%"=="true" (
    call "%~dp0scripts\setup\install-deps.bat"
    if errorlevel 1 exit /b 1
) else (
    echo [INFO] Preserving the existing main/image environment. No dependency upgrade requested.
)

echo [3/5] Setting up scam detection environment (.venv-scam)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup\install-scam.ps1"
if errorlevel 1 (
    echo [ERROR] Scam environment setup failed.
    exit /b 1
)

echo [4/5] Checking model artifacts...
if exist "%~dp0exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip" (
    "%~dp0.venv-scam\Scripts\python.exe" "%~dp0scripts\setup\install-scam-model.py" --package "%~dp0exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip"
    if errorlevel 1 exit /b 1
) else (
    if not exist "%~dp0models\scam_message\artifacts\model.safetensors" (
        echo [ERROR] model.safetensors is missing!
        echo Please copy model.safetensors or place TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip in exports\
        exit /b 1
    )
)

echo Setting up isolated phishing runtime (.venv-phishing) and model artifacts...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup\install-phishing.ps1"
if errorlevel 1 exit /b 1

echo [5/5] Installing Frontend dependencies...
cd /d "%~dp0frontend"
call npm ci
if errorlevel 1 exit /b 1
cd /d "%~dp0"

echo.
echo [VERIFICATION] Verifying model integrity...
"%~dp0.venv-scam\Scripts\python.exe" "%~dp0scripts\checks\verify-scam.py"
if errorlevel 1 (
    echo [ERROR] Scam verification failed.
    exit /b 1
)

echo.
echo =======================================================
echo  Setup Completed Successfully!
echo  To start the application, run: .\start-dev.bat
echo =======================================================
exit /b 0

:setup_phishing_only
call "%~dp0setup-phishing.bat" %2 %3 %4 %5
exit /b %errorlevel%

:setup_scam_only
call "%~dp0setup-scam.bat" %2 %3 %4 %5
exit /b %errorlevel%

:verify_all_only
echo [VERIFICATION] Verifying scam model...
"%~dp0.venv-scam\Scripts\python.exe" "%~dp0scripts\checks\verify-scam.py"
if errorlevel 1 exit /b 1
echo [VERIFICATION] Verifying phishing model...
"%~dp0.venv-phishing\Scripts\python.exe" "%~dp0scripts\packaging\package-phishing-team.py" --verify
if errorlevel 1 exit /b 1
echo.
echo [PASS] All models and checksums verified successfully.
exit /b 0
