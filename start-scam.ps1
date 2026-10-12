param([switch]$Portable)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv-scam\Scripts\python.exe'
if (!(Test-Path -LiteralPath $taskPython)) { throw 'Run .\install-scam.ps1 first.' }
if (!(Test-Path -LiteralPath (Join-Path $taskRoot '.env'))) {
    $taskSecret = & $taskPython -c 'import secrets; print(secrets.token_urlsafe(48))'
    @" 
ENVIRONMENT=dev
ALLOW_MOCK_AUTH=false
JWT_SECRET_KEY=$taskSecret
KAFKA_ENABLED=false
SCAM_OPTIONAL_ANALYSIS_ENABLED=false
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
"@ | Set-Content -LiteralPath (Join-Path $taskRoot '.env') -Encoding utf8
}
$env:PYTHONPATH = $taskRoot
$env:PYTHONUTF8 = '1'
$env:KAFKA_ENABLED = 'false'
if ($Portable) { $env:DATABASE_URL = 'sqlite+aiosqlite:///' + (Join-Path $taskRoot 'portable-state.sqlite').Replace('\','/') }
$taskLogs = Join-Path $taskRoot 'runtime-logs'
New-Item -ItemType Directory -Force -Path $taskLogs | Out-Null
$taskProcesses = @()
$taskPorts = @(8005,8001,8002,8000)
if ($Portable) { $taskPorts += 5173 }
foreach ($taskPortCheck in $taskPorts) {
    if (Get-NetTCPConnection -LocalPort $taskPortCheck -State Listen -ErrorAction SilentlyContinue) { throw "Port $taskPortCheck is already in use. Use the existing services or stop their own launcher first." }
}
foreach ($taskService in @(
    @('scam','services.scam_message.app.main:app',8005),
    @('auth','services.auth.app.main:app',8001),
    @('scan','services.scan_management.app.main:app',8002),
    @('gateway','gateway.app.main:app',8000))) {
    $taskPort = [int]$taskService[2]
    if (Get-NetTCPConnection -LocalPort $taskPort -State Listen -ErrorAction SilentlyContinue) { throw "Port $taskPort is already in use. Use the existing services or stop their own launcher first." }
    $taskServicePython = $taskPython
    if ($taskService[0] -eq 'scan' -and !$Portable) {
        $taskServicePython = Join-Path $taskRoot '.venv\Scripts\python.exe'
        if (!(Test-Path -LiteralPath $taskServicePython)) { throw 'Main scanner requires your existing image .venv. Use -Portable only for the scam-only export.' }
    }
    $taskProcess = Start-Process -FilePath $taskServicePython -ArgumentList @('-m','uvicorn',$taskService[1],'--host','127.0.0.1','--port',$taskPort) -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskLogs ($taskService[0]+'.out.log')) -RedirectStandardError (Join-Path $taskLogs ($taskService[0]+'.err.log'))
    $taskProcesses += @{id=$taskProcess.Id;service=$taskService[0];module=$taskService[1];python=$taskServicePython}
    $taskProcesses | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskLogs 'processes.json') -Encoding utf8
}
if ($Portable) {
    $taskDirectoryArgument = '"' + (Join-Path $taskRoot 'frontend\dist') + '"'
    $taskProcess = Start-Process -FilePath $taskPython -ArgumentList @('-m','http.server','5173','--bind','127.0.0.1','--directory',$taskDirectoryArgument) -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskLogs 'frontend.out.log') -RedirectStandardError (Join-Path $taskLogs 'frontend.err.log')
    $taskProcesses += @{id=$taskProcess.Id;service='frontend';module='http.server';python=$taskPython}
}
$taskProcesses | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskLogs 'processes.json') -Encoding utf8
$taskChecks = @{
    scam = 'http://127.0.0.1:8005/ready'
    auth = 'http://127.0.0.1:8001/health'
    scan = 'http://127.0.0.1:8002/health'
    gateway = 'http://127.0.0.1:8000/health'
}
if ($Portable) { $taskChecks.frontend = 'http://127.0.0.1:5173/' }
$taskDeadline = (Get-Date).AddSeconds(45)
do {
    $taskPending = @()
    foreach ($taskName in $taskChecks.Keys) {
        try { Invoke-WebRequest -UseBasicParsing -Uri $taskChecks[$taskName] -TimeoutSec 2 | Out-Null }
        catch { $taskPending += $taskName }
    }
    if ($taskPending.Count -eq 0) { break }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $taskDeadline)
if ($taskPending.Count -gt 0) {
    & (Join-Path $taskRoot 'stop-scam.ps1')
    throw ('Services failed readiness: ' + ($taskPending -join ', ') + '. Inspect runtime-logs/*.err.log. No successful launch is claimed.')
}
Write-Host 'Local services and scam model are ready. Website: http://localhost:5173 (main checkout: start npm run dev in frontend). Run scripts/smoke-scam.py for actual inference/auth validation.'
