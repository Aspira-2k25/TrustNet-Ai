$ErrorActionPreference = 'Stop'
$taskRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$taskPython = Join-Path $taskRoot '.venv-scam\Scripts\python.exe'
& (Join-Path $PSScriptRoot 'ensure-python-env.ps1') -Environment '.venv-scam'
& $taskPython -m pip install -r (Join-Path $taskRoot 'services/scam_message/requirements-portable.txt')
if ($LASTEXITCODE -ne 0) { throw 'Scam dependencies failed to install; existing image environment was not changed.' }
& $taskPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Scam dependency consistency check failed.' }
# Ensure .env exists so launcher doesn't fail
$envFile = Join-Path $taskRoot '.env'
$envExample = Join-Path $taskRoot '.env.example'
if (!(Test-Path -LiteralPath $envFile) -and (Test-Path -LiteralPath $envExample)) {
    Copy-Item -LiteralPath $envExample -Destination $envFile
    Write-Host 'Created .env from .env.example' -ForegroundColor Cyan
}

Write-Host 'Scam environment ready. Existing image .venv was preserved.'
