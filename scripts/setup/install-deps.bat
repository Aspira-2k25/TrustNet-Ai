@echo off
setlocal
set "TASK_ROOT=%~dp0..\..\"

powershell -NoProfile -ExecutionPolicy Bypass -File "%TASK_ROOT%scripts\setup\install-deps.ps1"
if errorlevel 1 exit /b 1

endlocal