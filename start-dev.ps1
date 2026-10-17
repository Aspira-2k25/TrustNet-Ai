# TrustNet AI — PowerShell Local Development Launcher
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         TrustNet AI - Local Development Launcher      " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    Write-Host "[ERROR] Virtual environment .venv not found." -ForegroundColor Red
    Write-Host "Run: python -m venv .venv" -ForegroundColor Yellow
    Write-Host "Then: .venv\Scripts\Activate.ps1; pip install -e shared/" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/3] Checking Apache Kafka 3.7 (Docker)..." -ForegroundColor Green
$phishingKafka = 'false'
docker info > $null 2>&1
if ($LASTEXITCODE -eq 0) {
    try {
        & "$PSScriptRoot/scripts/start-phishing-infrastructure.ps1"
        $phishingKafka = 'true'
    } catch {
        Write-Host "[NOTE] Phishing startup failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[NOTE] Docker is offline; microservices will run in standalone REST mode." -ForegroundColor Yellow
}

Write-Host "[2/3] Starting backend processes..." -ForegroundColor Green
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$PWD'; & '$PWD\.venv\Scripts\python.exe' -m uvicorn gateway.app.main:app --port 8000 --reload"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$PWD'; & '$PWD\.venv\Scripts\python.exe' -m uvicorn services.auth.app.main:app --port 8001 --reload"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:KAFKA_ENABLED='$phishingKafka'; & '$PWD\.venv\Scripts\python.exe' -m uvicorn services.scan_management.app.main:app --port 8002 --reload"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$PWD'; & '$PWD\.venv\Scripts\python.exe' -m uvicorn services.image_deepfake.app.main:app --port 8003 --reload"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$PWD'; & '$PWD\.venv\Scripts\python.exe' -m uvicorn services.trust_engine.app.main:app --port 8004 --reload"

$scamPython = Join-Path $PWD '.venv-scam/Scripts/python.exe'
if (Test-Path -LiteralPath $scamPython) {
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$PWD'; & '$scamPython' -m uvicorn services.scam_message.app.main:app --port 8005"
} else {
    Write-Host "Scam service not started: install its separate environment per services/scam_message/README.md." -ForegroundColor Yellow
}
Write-Host "[3/3] Launching React Frontend (5173)..." -ForegroundColor Green
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev"

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Launch commands issued; check service health before use." -ForegroundColor Green
Write-Host " - Frontend UI:   http://localhost:5173" -ForegroundColor White
Write-Host " - API Gateway:   http://localhost:8000/docs" -ForegroundColor White
Write-Host " - Auth Swagger:  http://localhost:8001/docs" -ForegroundColor White
Write-Host "=======================================================" -ForegroundColor Cyan
