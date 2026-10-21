param([ValidateSet('all','image')][string]$Service = 'all')
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
    if ($Service -ne 'all' -and $taskEntry.service -ne $Service) { continue }
    $taskProcessId = 0
    if (-not [int]::TryParse([string]$taskEntry.id, [ref]$taskProcessId) -or $taskProcessId -le 0 -or -not $taskEntry.python -or -not $taskEntry.module) {
        throw 'Invalid launcher process record. No process was selected by port number.'
    }
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$taskProcessId"
    if ($taskProcess -and $taskProcess.ExecutablePath -eq $taskEntry.python -and $taskProcess.CommandLine.Contains($taskEntry.module)) {
        # Stop the verified launcher-owned tree, including spawned CPU localizer workers.
        & taskkill.exe /PID $taskProcessId /T /F | Out-Null
        if ($LASTEXITCODE -ne 0 -and (Get-Process -Id $taskProcessId -ErrorAction SilentlyContinue)) {
            throw "Could not stop owned process $taskProcessId"
        }
    }
}
Write-Host 'Stopped only matching processes from this launcher. Databases and logs preserved.'
