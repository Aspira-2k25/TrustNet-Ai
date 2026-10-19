param([string]$Manifest = '', [switch]$Kafka, [switch]$Background)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $taskRoot
if (-not $Manifest) {
    $taskModernBundle = if ($env:PHISHING_MODERN_BUNDLE) {$env:PHISHING_MODERN_BUNDLE} else {'regional_recall_v1'}
    if ($taskModernBundle -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid PHISHING_MODERN_BUNDLE folder name.' }
    $Manifest = "models/phishing_url/checkpoints/$taskModernBundle/manifest.json"
}
$env:PHISHING_MODEL_MANIFEST = (Resolve-Path -LiteralPath $Manifest).Path
$env:PHISHING_KAFKA_ENABLED = if ($Kafka) {'true'} else {'false'}
$env:HF_HUB_OFFLINE = '1'
$taskPython = Join-Path $taskRoot '.venv-phishing\Scripts\python.exe'
if (!(Test-Path -LiteralPath $taskPython)) { throw 'Run .\scripts/setup/install-phishing.ps1 first. The image environment is not used for phishing.' }
if (!$Background) {
    & $taskPython -m uvicorn services.phishing_url.app.main:app --host 127.0.0.1 --port 8007
    exit $LASTEXITCODE
}
try {
    Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8007/ready -TimeoutSec 2 | Out-Null
    Write-Host 'Existing phishing service is ready; preserving it.'
    return
} catch {}
if (Get-NetTCPConnection -LocalPort 8007 -State Listen -ErrorAction SilentlyContinue) {
    # Docker publishes its port before model/broker readiness. Wait only for the
    # identified project service, never mistake an arbitrary listener for ready.
    $taskDockerService = ''
    try { $taskDockerService = & docker ps --filter 'publish=8007' --filter 'label=com.docker.compose.service=phishing' --format '{{.Names}}' 2>$null } catch {}
    if (!$taskDockerService) { throw 'Port 8007 is occupied but phishing is not ready; inspect its owner.' }
    Write-Host 'Waiting for the existing Docker phishing model and Kafka connection...'
    $taskDockerDeadline = (Get-Date).AddSeconds(120)
    do {
        try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8007/ready -TimeoutSec 2 | Out-Null; Write-Host 'Docker phishing model ready.'; return } catch {}
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $taskDockerDeadline)
    throw 'Docker phishing readiness failed; inspect docker logs. No duplicate process was started.'
}
$taskLogs = Join-Path $taskRoot 'runtime-logs'
New-Item -ItemType Directory -Force -Path $taskLogs | Out-Null
$taskModule = 'services.phishing_url.app.main:app'
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList @('-m','uvicorn',$taskModule,'--host','127.0.0.1','--port','8007') -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskLogs 'phishing.out.log') -RedirectStandardError (Join-Path $taskLogs 'phishing.err.log')
@(@{id=$taskProcess.Id;service='phishing';module=$taskModule;python=$taskPython}) | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskLogs 'phishing-processes.json') -Encoding utf8
$taskDeadline = (Get-Date).AddSeconds(60)
do {
    if ($taskProcess.HasExited) { throw 'Phishing exited; inspect runtime-logs/phishing.err.log.' }
    try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8007/ready -TimeoutSec 2 | Out-Null; Write-Host 'Phishing model ready on port 8007.'; return } catch {}
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $taskDeadline)
Stop-Process -Id $taskProcess.Id -ErrorAction SilentlyContinue
throw 'Phishing model readiness timed out; inspect runtime-logs/phishing.err.log.'
