$ErrorActionPreference = 'Stop'
$taskRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
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
function Install-ScamDependencies {
    param([string[]]$PipArguments, [string]$Description)
    for ($taskAttempt = 1; $taskAttempt -le 3; $taskAttempt++) {
        # Retry the full install too: older pip versions do not resume timed-out downloads.
        & $taskPython -m pip install --timeout 120 --retries 5 @PipArguments
        if ($LASTEXITCODE -eq 0) { return }
        if ($taskAttempt -lt 3) {
            Write-Warning "$Description installation attempt $taskAttempt failed; retrying with cached downloads..."
        }
    }
    throw "$Description installation failed after 3 attempts. Check your internet connection and rerun .\setup-scam.bat; completed downloads are cached."
}
Install-ScamDependencies -PipArguments @('torch==2.6.0', '--index-url', 'https://download.pytorch.org/whl/cpu') -Description 'CPU PyTorch'
Install-ScamDependencies -PipArguments @('-r', (Join-Path $taskRoot 'services/scam_message/requirements-portable.txt')) -Description 'Scam dependencies'
& $taskPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Scam dependency consistency check failed.' }
# Normalize line endings only when the result matches the approved artifact checksum.
$artifactsDir = Join-Path $taskRoot 'models\scam_message\artifacts'
$taskManifestPath = Join-Path $artifactsDir 'manifest.json'
if (Test-Path -LiteralPath $taskManifestPath) {
    $taskManifest = Get-Content -LiteralPath $taskManifestPath -Raw | ConvertFrom-Json
    foreach ($textFileName in @('vocab.txt', 'tokenizer.json', 'tokenizer_config.json', 'config.json', 'special_tokens_map.json', 'runtime.json')) {
        $filePath = Join-Path $artifactsDir $textFileName
        if (Test-Path -LiteralPath $filePath) {
            try {
                $bytes = [System.IO.File]::ReadAllBytes($filePath)
                $text = [System.Text.Encoding]::UTF8.GetString($bytes)
                $taskExpectedHash = $taskManifest.files.$textFileName
                if (-not $taskExpectedHash -or (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash -eq $taskExpectedHash) { continue }
                $taskLfText = $text.Replace("`r`n", "`n")
                foreach ($taskCandidateText in @($taskLfText, $taskLfText.Replace("`n", "`r`n"))) {
                    $taskCandidateBytes = [System.Text.Encoding]::UTF8.GetBytes($taskCandidateText)
                    $taskHasher = [System.Security.Cryptography.SHA256]::Create()
                    try { $taskHash = [BitConverter]::ToString($taskHasher.ComputeHash($taskCandidateBytes)).Replace('-', '').ToLowerInvariant() }
                    finally { $taskHasher.Dispose() }
                    if ($taskHash -eq $taskExpectedHash) {
                        [System.IO.File]::WriteAllBytes($filePath, $taskCandidateBytes)
                        break
                    }
                }
            } catch {}
        }
    }
}

# Ensure .env exists so launcher doesn't fail
$envFile = Join-Path $taskRoot '.env'
$envExample = Join-Path $taskRoot '.env.example'
if (!(Test-Path -LiteralPath $envFile) -and (Test-Path -LiteralPath $envExample)) {
    Copy-Item -LiteralPath $envExample -Destination $envFile
    Write-Host 'Created .env from .env.example' -ForegroundColor Cyan
}

Write-Host 'Scam environment ready. Existing image .venv was preserved.'
