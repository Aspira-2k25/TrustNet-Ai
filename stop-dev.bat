@echo off
setlocal
cd /d "%~dp0"
echo Stopping TrustNet AI services...

REM 1. Run stop-scam.ps1 if present
if exist "%~dp0stop-scam.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-scam.ps1" >nul 2>&1
)

REM 2. Cleanly stop any processes still listening on project ports (8000-8005, 5173)
powershell -NoProfile -Command ^
    "$ports = @(8000, 8001, 8002, 8003, 8004, 8005, 5173); " ^
    "$conns = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $ports -contains $_.LocalPort }; " ^
    "if ($conns) { " ^
    "    $pids = $conns.OwningProcess | Select-Object -Unique; " ^
    "    foreach ($pidToKill in $pids) { " ^
    "        try { Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue } catch {} " ^
    "    } " ^
    "    Write-Host '[OK] Stopped processes on ports: ' (($conns.LocalPort | Sort-Object -Unique) -join ', '); " ^
    "} else { " ^
    "    Write-Host '[OK] No background services were running.'; " ^
    "}"

echo [OK] All TrustNet AI terminals and background ports are now free.
endlocal
