@echo off
setlocal
set "TASK_ROOT=%~dp0..\..\"
cd /d "%TASK_ROOT%"

echo =======================================================
echo     TrustNet AI - Scam Module Setup
echo  (Existing Image Environment .venv will NOT be touched)
echo =======================================================

echo [1/3] Setting up scam virtual environment (.venv-scam)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%TASK_ROOT%scripts\setup\install-scam.ps1"
if errorlevel 1 (
    echo [ERROR] Scam environment setup failed. Check if Python 3.11 is installed.
    exit /b 1
)

echo [2/3] Checking model artifacts...
if not exist "%TASK_ROOT%models\scam_message\artifacts\model.safetensors" (
    if exist "%TASK_ROOT%exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip" (
        echo [INFO] model.safetensors missing; extracting from exports ZIP...
        "%TASK_ROOT%.venv-scam\Scripts\python.exe" "%TASK_ROOT%scripts\setup\install-scam-model.py" --package "%TASK_ROOT%exports\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip"
    ) else (
        echo [ERROR] model.safetensors is missing!
        echo Please copy model.safetensors or the complete artifacts folder into:
        echo   models\scam_message\artifacts\
        exit /b 1
    )
)

REM Ensure artifact text files use LF line endings (prevents Windows CRLF checksum error)
powershell -NoProfile -Command "foreach ($f in @('vocab.txt','tokenizer.json','tokenizer_config.json','config.json','special_tokens_map.json')) { $p = Join-Path '%TASK_ROOT%models\scam_message\artifacts' $f; if (Test-Path $p) { $b = [System.IO.File]::ReadAllBytes($p); $t = [System.Text.Encoding]::UTF8.GetString($b); if ($t.Contains(\"`r`n\")) { [System.IO.File]::WriteAllBytes($p, [System.Text.Encoding]::UTF8.GetBytes($t.Replace(\"`r`n\", \"`n\"))) } } }"

echo [3/3] Verifying Scam Model Integrity...
"%TASK_ROOT%.venv-scam\Scripts\python.exe" "%TASK_ROOT%scripts\checks\verify-scam.py"
if errorlevel 1 (
    echo [ERROR] Scam verification failed.
    exit /b 1
)

echo.
echo =======================================================
echo  Scam Module Setup Successful!
echo  Your existing image environment (.venv) was preserved.
echo  To start the full project, run: .\start-dev.bat
echo =======================================================
endlocal
