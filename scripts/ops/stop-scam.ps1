$ErrorActionPreference = 'Stop'
$taskEntries = @()
foreach ($taskStateFile in @('processes.json','web-processes.json','phishing-processes.json')) {
    $taskFile = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) ('runtime-logs\' + $taskStateFile)
    if (Test-Path -LiteralPath $taskFile) {
        # Windows PowerShell 5.1 can return a JSON array as one pipeline item.
        # Enumerate it explicitly so each process ID remains a scalar.
        $taskParsed = Get-Content -LiteralPath $taskFile -Raw | ConvertFrom-Json
        foreach ($taskRecord in $taskParsed) { $taskEntries += $taskRecord }
    }
}
foreach ($taskEntry in $taskEntries) {
    $taskProcessId = 0
    if (-not [int]::TryParse([string]$taskEntry.id, [ref]$taskProcessId) -or $taskProcessId -le 0 -or -not $taskEntry.python -or -not $taskEntry.module) {
        throw 'Invalid launcher process record. No process was selected by port number.'
    }
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$taskProcessId"
    if ($taskProcess -and $taskProcess.ExecutablePath -eq $taskEntry.python -and $taskProcess.CommandLine.Contains($taskEntry.module)) {
        foreach ($taskChild in (Get-CimInstance Win32_Process -Filter "ParentProcessId=$($taskEntry.id)")) {
            if ($taskChild.CommandLine -and $taskChild.CommandLine.Contains($taskEntry.module)) { Stop-Process -Id $taskChild.ProcessId }
        }
        Stop-Process -Id $taskEntry.id -ErrorAction SilentlyContinue
    }
}
Write-Host 'Stopped only matching processes from this launcher. Databases and logs preserved.'
