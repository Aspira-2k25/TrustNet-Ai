# TrustNet AI - Dependency Installer
$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
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

Install-Requirements -WorkingDirectory $repoRoot -Arguments @('-e', 'shared/') -Label 'shared editable package'
Install-Requirements -WorkingDirectory (Join-Path $repoRoot 'services\auth') -Arguments @('-r', 'requirements.txt') -Label 'services/auth'
Install-Requirements -WorkingDirectory (Join-Path $repoRoot 'services\scan_management') -Arguments @('-r', 'requirements.txt') -Label 'services/scan_management'
Install-Requirements -WorkingDirectory (Join-Path $repoRoot 'models\image_deepfake') -Arguments @('-r', 'requirements.txt') -Label 'models/image_deepfake'
Install-Requirements -WorkingDirectory (Join-Path $repoRoot 'services\image_deepfake') -Arguments @('-r', 'requirements.txt') -Label 'services/image_deepfake'
Install-Requirements -WorkingDirectory (Join-Path $repoRoot 'services\trust_engine') -Arguments @('-r', 'requirements.txt') -Label 'services/trust_engine'
Install-Requirements -WorkingDirectory (Join-Path $repoRoot 'gateway') -Arguments @('-r', 'requirements.txt') -Label 'gateway'

Write-Host '[DONE] All dependency installs completed.' -ForegroundColor Green