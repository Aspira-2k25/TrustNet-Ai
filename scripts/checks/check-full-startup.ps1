param([ValidateRange(5,900)][int]$StartupTimeoutSeconds = 240)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$taskChecks = @{
    phishing = 'http://127.0.0.1:8007/ready'
    image = 'http://127.0.0.1:8003/health'
    trust = 'http://127.0.0.1:8004/health'
    frontend = 'http://localhost:5173/'
}
$taskDeadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
$taskNextNotice = (Get-Date).AddSeconds(15)
Write-Host "Waiting up to $StartupTimeoutSeconds seconds for image, trust and frontend startup..."
do {
    $taskPending = @()
    foreach ($taskName in $taskChecks.Keys) {
        try { Invoke-WebRequest -UseBasicParsing -Uri $taskChecks[$taskName] -TimeoutSec 2 | Out-Null }
        catch { $taskPending += $taskName }
    }
    if ($taskPending.Count -eq 0) { break }
    if ((Get-Date) -ge $taskNextNotice) {
        Write-Host ('Still waiting for: ' + ($taskPending -join ', ') + '. Startup output is in runtime-logs/<service>.err.log.')
        $taskNextNotice = (Get-Date).AddSeconds(15)
    }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $taskDeadline)
if ($taskPending.Count -gt 0) {
    Write-Host ('[ERROR] Startup incomplete after ' + $StartupTimeoutSeconds + ' seconds: ' + ($taskPending -join ', ') + '. Inspect runtime-logs/<service>.err.log and .out.log. Healthy services were left running.')
    exit 1
}
& (Join-Path $taskRoot '.venv-scam\Scripts\python.exe') (Join-Path $taskRoot 'scripts/checks/smoke-message-url.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'Local service HTTP checks and real scam/URL inference passed. Website: http://localhost:5173'
Write-Host 'Image health does not certify Hugging Face inference; check analyzer availability in an actual image result.'

