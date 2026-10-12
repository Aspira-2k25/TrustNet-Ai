$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv-scam\Scripts\python.exe'
if (!(Test-Path -LiteralPath $taskPython)) {
    $created = $false
    try {
        & py -3.11 -m venv (Join-Path $taskRoot '.venv-scam')
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $taskPython)) { $created = $true }
    } catch {}
    if (-not $created) {
        & python -m venv (Join-Path $taskRoot '.venv-scam')
    }
    if (!(Test-Path -LiteralPath $taskPython)) { throw 'Failed to create .venv-scam. Install Python 3.11 and ensure it is in PATH.' }
}
& $taskPython -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw 'CPU PyTorch installation failed.' }
& $taskPython -m pip install -r (Join-Path $taskRoot 'requirements-scam-portable.txt')
if ($LASTEXITCODE -ne 0) { throw 'Scam dependencies failed to install; existing image environment was not changed.' }
& $taskPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
Write-Host 'Scam environment ready. Existing image .venv was preserved.'
