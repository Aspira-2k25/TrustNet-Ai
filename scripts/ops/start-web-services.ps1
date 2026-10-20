# Launch remaining website services with persistent output, preserving healthy processes.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$taskLogs = Join-Path $taskRoot 'runtime-logs'
New-Item -ItemType Directory -Force -Path $taskLogs | Out-Null
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
$taskState = Join-Path $taskLogs 'web-processes.json'
$taskEntries = @()
if (Test-Path -LiteralPath $taskState) {
    $taskParsed = Get-Content -LiteralPath $taskState -Raw | ConvertFrom-Json
    foreach ($taskRecord in $taskParsed) { $taskEntries += $taskRecord }
}
foreach ($taskService in @(
    @('image','services.image_deepfake.app.main:app',8003),
    @('trust','services.trust_engine.app.main:app',8004),
    @('frontend','vite',5173))) {
    $taskName = $taskService[0]
    $taskPort = [int]$taskService[2]
    $taskUrl = if ($taskName -eq 'image') {"http://127.0.0.1:$taskPort/ready"} elseif ($taskName -eq 'frontend') {'http://localhost:5173/'} else {"http://127.0.0.1:$taskPort/health"}
    $taskHealthy = $false
    try { Invoke-WebRequest -UseBasicParsing -Uri $taskUrl -TimeoutSec 2 | Out-Null; $taskHealthy = $true } catch {}
    if ($taskHealthy) { Write-Host "$taskName already responds; preserving its process."; continue }
    if (Get-NetTCPConnection -LocalPort $taskPort -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $taskPort is occupied but $taskName is not healthy. Inspect its existing process; no duplicate was launched."
    }
    $taskExecutable = $taskPython
    $taskWorkingDirectory = $taskRoot
    $taskArguments = @('-m','uvicorn',$taskService[1],'--host','127.0.0.1','--port',"$taskPort")
    if ($taskName -eq 'frontend') {
        $taskExecutable = (Get-Command node.exe -ErrorAction Stop).Source
        $taskWorkingDirectory = Join-Path $taskRoot 'frontend'
        $taskVite = Join-Path $taskWorkingDirectory 'node_modules\vite\bin\vite.js'
        if (!(Test-Path -LiteralPath $taskVite)) { throw 'Frontend dependencies missing; run npm ci in frontend.' }
        $taskArguments = @(('"'+$taskVite+'"'),'--host','localhost','--port','5173','--strictPort')
    }
    $taskProcess = Start-Process -FilePath $taskExecutable -ArgumentList $taskArguments -WorkingDirectory $taskWorkingDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskLogs "$taskName.out.log") -RedirectStandardError (Join-Path $taskLogs "$taskName.err.log")
    $taskEntries = @($taskEntries | Where-Object { $_.service -ne $taskName })
    $taskEntries += @{id=$taskProcess.Id;service=$taskName;module=$taskService[1];python=$taskExecutable}
    ConvertTo-Json -InputObject @($taskEntries) | Set-Content -LiteralPath $taskState -Encoding utf8
    Write-Host "Started $taskName; startup output: runtime-logs/$taskName.err.log"
}
