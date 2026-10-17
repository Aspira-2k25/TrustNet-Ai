param([string]$Manifest = 'models/phishing_url/checkpoints/modern_v5/manifest.json', [switch]$Kafka)
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$env:PHISHING_MODEL_MANIFEST = (Resolve-Path -LiteralPath $Manifest).Path
$env:PHISHING_KAFKA_ENABLED = if ($Kafka) {'true'} else {'false'}
$env:HF_HUB_OFFLINE = '1'
& "$taskRoot/.venv/Scripts/python.exe" -m uvicorn services.phishing_url.app.main:app --host 127.0.0.1 --port 8007
