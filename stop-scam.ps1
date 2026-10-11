$taskFile = Join-Path $PSScriptRoot 'runtime-logs\processes.json'
if (!(Test-Path -LiteralPath $taskFile)) { return }
foreach ($taskEntry in (Get-Content -LiteralPath $taskFile -Raw | ConvertFrom-Json)) {
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskEntry.id)"
    if ($taskProcess -and $taskProcess.ExecutablePath -eq $taskEntry.python -and $taskProcess.CommandLine.Contains($taskEntry.module)) {
        foreach ($taskChild in (Get-CimInstance Win32_Process -Filter "ParentProcessId=$($taskEntry.id)")) {
            if ($taskChild.CommandLine -and $taskChild.CommandLine.Contains($taskEntry.module)) { Stop-Process -Id $taskChild.ProcessId }
        }
        Stop-Process -Id $taskEntry.id -ErrorAction SilentlyContinue
    }
}
Write-Host 'Stopped only matching processes from this launcher. Databases and logs preserved.'
