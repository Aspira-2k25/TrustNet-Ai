param([switch]$Baseline, [switch]$Forensics, [switch]$Offline)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskModernBundle = if ($env:PHISHING_MODERN_BUNDLE) {$env:PHISHING_MODERN_BUNDLE} else {'regional_recall_v1'}
if ($taskModernBundle -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid PHISHING_MODERN_BUNDLE folder name.' }
$manifest = if ($Baseline) {'models/phishing_url/checkpoints/baseline/rf.json'} else {"models/phishing_url/checkpoints/$taskModernBundle/manifest.json"}
if (-not (Test-Path -LiteralPath $manifest)) {
    throw "Phishing model missing: $manifest. Restore its checked bundle before launching."
}
function Invoke-PhishingDocker {
    param([string[]]$DockerArguments, [switch]$Quiet)
    # Native stderr warnings are not failures in Windows PowerShell.
    $ErrorActionPreference = 'Continue'
    if ($Quiet) { & docker @DockerArguments *> $null }
    else { & docker @DockerArguments 2>&1 | ForEach-Object { Write-Host "$_" } }
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed (exit $LASTEXITCODE): docker $($DockerArguments -join ' ')" }
}
Invoke-PhishingDocker -DockerArguments @('info') -Quiet
$composeFiles = @('-f', 'docker-compose.yml', '-f', 'services/phishing_url/compose.phishing.yml')
if (-not $Baseline) { $composeFiles += @('-f', 'services/phishing_url/compose.modern.yml') }
if (-not $Offline) {
    if (-not $env:PHISHING_COLLECTOR_TOKEN) {
        $taskSecretDirectory = Join-Path $taskRoot 'runtime_state/phishing'
        New-Item -ItemType Directory -Path $taskSecretDirectory -Force | Out-Null
        $taskSecretPath = Join-Path $taskSecretDirectory 'collector-token'
        if (-not (Test-Path -LiteralPath $taskSecretPath)) {
            $taskSecretBytes = New-Object byte[] 32
            $taskRandom = [System.Security.Cryptography.RandomNumberGenerator]::Create()
            try { $taskRandom.GetBytes($taskSecretBytes) } finally { $taskRandom.Dispose() }
            [System.Convert]::ToBase64String($taskSecretBytes) | Set-Content -LiteralPath $taskSecretPath -NoNewline
        }
        $env:PHISHING_COLLECTOR_TOKEN = (Get-Content -LiteralPath $taskSecretPath -Raw).Trim()
    }
    $composeFiles += @('-f', 'services/phishing_url/compose.forensics.yml')
}
$taskServices = if (-not $Offline) { @('phishing', 'phishing-collector') } else { @('phishing') }
Invoke-PhishingDocker -DockerArguments (@('compose') + $composeFiles + @('up', '-d', '--build') + $taskServices)
Write-Host 'Phishing worker launched on 8007. Scan Management must run with KAFKA_ENABLED=true.'
