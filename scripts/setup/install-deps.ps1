# TrustNet AI - Dependency Installer
$ErrorActionPreference = 'Stop'

$repoRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Host '[ERROR] Virtual environment .venv not found.' -ForegroundColor Red
    Write-Host 'Create it first: python -m venv .venv' -ForegroundColor Yellow
    exit 1
}

function Install-Requirements {
    param(
        [string]$WorkingDirectory,
        [string[]]$Arguments,
        [string]$Label
    )

    Write-Host "[INSTALL] $Label" -ForegroundColor Cyan
    Push-Location $WorkingDirectory
    try {
        & $python -m pip install @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "pip install failed for $Label"
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "[INSTALL] PyTorch CPU (official wheel)" -ForegroundColor Cyan
& $python -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw 'CPU PyTorch installation failed.' }

Install-Requirements -WorkingDirectory $repoRoot -Arguments @('-e','shared/') -Label 'shared package'
Install-Requirements -WorkingDirectory $repoRoot -Arguments @('-r','requirements/runtime.txt') -Label 'pinned main runtime'
Write-Host '[DONE] Main dependencies installed. Scam and phishing use separate environments.' -ForegroundColor Green
