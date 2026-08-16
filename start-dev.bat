@echo off
echo =======================================================
echo          TrustNet AI - Local Development Launcher
echo =======================================================
echo.

REM Check Python virtual environment
if not exist ".venv" (
    echo [ERROR] Virtual environment .venv not found.
    echo Please create it first: python -m venv .venv
    echo Then run: .venv\Scripts\activate ^&^& pip install -e shared/
    pause
    exit /b 1
)

echo [1/3] Starting Apache Kafka 3.7 (Docker)...
docker compose up -d kafka

echo [2/3] Launching backend microservices in separate windows...
start "API Gateway (8000)" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn gateway.app.main:app --port 8000 --reload"
start "Auth Service (8001)" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn services.auth.app.main:app --port 8001 --reload"
start "Scan Management (8002)" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn services.scan_management.app.main:app --port 8002 --reload"
start "Image Deepfake Worker (8003)" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn services.image_deepfake.app.main:app --port 8003 --reload"
start "Trust Engine (8004)" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn services.trust_engine.app.main:app --port 8004 --reload"

echo [3/3] Launching React Frontend (5173)...
start "React Frontend (5173)" cmd /k "cd frontend && npm run dev"

echo.
echo =======================================================
echo  All services launched!
echo  - Frontend: http://localhost:5173
echo  - API Gateway: http://localhost:8000/docs
echo =======================================================
