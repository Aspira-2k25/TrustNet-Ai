param([string]$Package = '')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $taskRoot

$taskPython = Join-Path $taskRoot '.venv-phishing\Scripts\python.exe'
if (!(Test-Path -LiteralPath $taskPython)) {
    Write-Host '[1/3] Creating isolated Python 3.11 virtual environment (.venv-phishing)...' -ForegroundColor Cyan
    $created = $false
    try {
        & py -3.11 -m venv (Join-Path $taskRoot '.venv-phishing')
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $taskPython)) { $created = $true }
    } catch {}
    if (-not $created) {
        & python -m venv (Join-Path $taskRoot '.venv-phishing')
    }
    if (!(Test-Path -LiteralPath $taskPython)) {
        throw 'Failed to create .venv-phishing. Python 3.11 is required. Ensure Python 3.11 is installed and in PATH.'
    }
}

Write-Host '[2/3] Installing isolated phishing runtime dependencies...' -ForegroundColor Cyan
$taskInstallSucceeded = $false
for ($taskAttempt = 1; $taskAttempt -le 3; $taskAttempt++) {
    # Retry the full install too: older pip versions do not resume timed-out downloads.
    & $taskPython -m pip install --timeout 120 --retries 5 -r (Join-Path $taskRoot 'services/phishing_url/requirements-runtime.txt')
    if ($LASTEXITCODE -eq 0) {
        $taskInstallSucceeded = $true
        break
    }
    if ($taskAttempt -lt 3) {
        Write-Warning "Dependency installation attempt $taskAttempt failed; retrying with cached downloads..."
    }
}
if (-not $taskInstallSucceeded) {
    throw 'Phishing dependency installation failed after 3 attempts. Check your internet connection and rerun .\setup-phishing.bat; completed downloads are cached.'
}

Write-Host '[3/3] Checking and verifying phishing model artifacts...' -ForegroundColor Cyan
if (!$Package) {
    $Package = Join-Path $taskRoot 'exports\TrustNet-Phishing-regional-recall-v1.zip'
}
if (Test-Path -LiteralPath $Package) {
    Write-Host "Extracting verified model package from $Package..." -ForegroundColor Cyan
    & $taskPython (Join-Path $taskRoot 'scripts/setup/install-phishing-model.py') $Package
    if ($LASTEXITCODE -ne 0) { throw 'Phishing artifact installation failed.' }
}

$checkpointDir = Join-Path $taskRoot 'models/phishing_url/checkpoints/regional_recall_v1'
if (!(Test-Path -LiteralPath (Join-Path $checkpointDir 'manifest.json'))) {
    Write-Host '[ERROR] Phishing model artifacts are missing!' -ForegroundColor Red
    Write-Host 'To fix this, please place the model release ZIP:' -ForegroundColor Yellow
    Write-Host "   $Package" -ForegroundColor White
    Write-Host 'Or copy the 8 model artifacts directly into:' -ForegroundColor Yellow
    Write-Host "   $checkpointDir" -ForegroundColor White
    throw 'Phishing model artifacts not found.'
}

& $taskPython (Join-Path $taskRoot 'scripts/packaging/package-phishing-team.py') --verify
if ($LASTEXITCODE -ne 0) {
    throw 'Checksum verification failed for phishing model artifacts.'
}

Write-Host 'Phishing environment and model ready. Existing image (.venv) and scam (.venv-scam) environments were preserved.' -ForegroundColor Green
