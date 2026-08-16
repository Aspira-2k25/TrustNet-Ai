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

Write-Host "[1/3] Starting Apache Kafka 3.7 (Docker)..." -ForegroundColor Green
docker compose up -d kafka

Write-Host "[2/3] Launching backend microservices in separate windows..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; & '$PWD\.venv\Scripts\python.exe' -m uvicorn gateway.app.main:app --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; & '$PWD\.venv\Scripts\python.exe' -m uvicorn services.auth.app.main:app --port 8001 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; & '$PWD\.venv\Scripts\python.exe' -m uvicorn services.scan_management.app.main:app --port 8002 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; & '$PWD\.venv\Scripts\python.exe' -m uvicorn services.image_deepfake.app.main:app --port 8003 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; & '$PWD\.venv\Scripts\python.exe' -m uvicorn services.trust_engine.app.main:app --port 8004 --reload"

Write-Host "[3/3] Launching React Frontend (5173)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev"

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " All services launched!" -ForegroundColor Green
Write-Host " - Frontend UI:   http://localhost:5173" -ForegroundColor White
Write-Host " - API Gateway:   http://localhost:8000/docs" -ForegroundColor White
Write-Host " - Auth Swagger:  http://localhost:8001/docs" -ForegroundColor White
Write-Host "=======================================================" -ForegroundColor Cyan
