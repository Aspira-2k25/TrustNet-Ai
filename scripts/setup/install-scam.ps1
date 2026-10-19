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
& $taskPython -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw 'CPU PyTorch installation failed.' }
& $taskPython -m pip install -r (Join-Path $taskRoot 'services/scam_message/requirements-portable.txt')
if ($LASTEXITCODE -ne 0) { throw 'Scam dependencies failed to install; existing image environment was not changed.' }
& $taskPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Scam dependency consistency check failed.' }
# Normalize any CRLF in model text artifacts to LF to guarantee checksum match on Windows
$artifactsDir = Join-Path $taskRoot 'models\scam_message\artifacts'
if (Test-Path -LiteralPath $artifactsDir) {
    foreach ($textFileName in @('vocab.txt', 'tokenizer.json', 'tokenizer_config.json', 'config.json', 'special_tokens_map.json')) {
        $filePath = Join-Path $artifactsDir $textFileName
        if (Test-Path -LiteralPath $filePath) {
            try {
                $bytes = [System.IO.File]::ReadAllBytes($filePath)
                $text = [System.Text.Encoding]::UTF8.GetString($bytes)
                if ($text.Contains("`r`n")) {
                    $clean = $text.Replace("`r`n", "`n")
                    [System.IO.File]::WriteAllBytes($filePath, [System.Text.Encoding]::UTF8.GetBytes($clean))
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
