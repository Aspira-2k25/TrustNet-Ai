param(
    [ValidateSet('.venv','.venv-scam','.venv-phishing')][string]$Environment = '.venv',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$taskEnvironment = Join-Path $taskRoot $Environment
$taskPython = Join-Path $taskEnvironment 'Scripts\python.exe'

if (Test-Path -LiteralPath $taskPython) {
    & $taskPython -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,11) else 1)'
    if ($LASTEXITCODE -ne 0) { throw "$Environment must use Python 3.11. Existing environment was preserved; create a compatible environment before continuing." }
    Write-Host "PASS: $Environment uses Python 3.11."
    return
}

$taskCommand = $null
$taskPrefix = @()
foreach ($taskCandidate in @('py.exe','python.exe')) {
    $taskResolved = Get-Command $taskCandidate -ErrorAction SilentlyContinue
    if (!$taskResolved) { continue }
    $taskArguments = @()
    if ($taskCandidate -eq 'py.exe') { $taskArguments = @('-3.11') }
    try { & $taskResolved.Source @taskArguments -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,11) else 1)' 2>$null }
    catch { continue }
    if ($LASTEXITCODE -eq 0) {
        $taskCommand = $taskResolved.Source
        $taskPrefix = $taskArguments
        break
    }
}
if (!$taskCommand) { throw 'Python 3.11 was not found. Install Python 3.11 with its launcher, reopen the terminal and rerun setup. Other versions are not silently used.' }
if ($CheckOnly) { Write-Host 'PASS: Python 3.11 is available.'; return }
& $taskCommand @taskPrefix -m venv $taskEnvironment
if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $taskPython)) { throw "Failed to create $Environment. No existing environment was deleted." }
Write-Host "Created $Environment with Python 3.11."
