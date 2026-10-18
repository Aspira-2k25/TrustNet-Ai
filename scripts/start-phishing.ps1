param([string]$Manifest = '', [switch]$Kafka)
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (-not $Manifest) {
    $taskModernBundle = if ($env:PHISHING_MODERN_BUNDLE) {$env:PHISHING_MODERN_BUNDLE} else {'regional_recall_v1'}
    if ($taskModernBundle -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid PHISHING_MODERN_BUNDLE folder name.' }
    $Manifest = "models/phishing_url/checkpoints/$taskModernBundle/manifest.json"
}
$env:PHISHING_MODEL_MANIFEST = (Resolve-Path -LiteralPath $Manifest).Path
$env:PHISHING_KAFKA_ENABLED = if ($Kafka) {'true'} else {'false'}
$env:HF_HUB_OFFLINE = '1'
& "$taskRoot/.venv/Scripts/python.exe" -m uvicorn services.phishing_url.app.main:app --host 127.0.0.1 --port 8007
