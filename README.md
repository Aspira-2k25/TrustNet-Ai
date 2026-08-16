# Trust Net (TrustNet AI)

Trust Net is a multi-service forensic platform for media authenticity analysis. It combines a React frontend, a FastAPI gateway, microservices, and a multi-signal image deepfake pipeline.

## Latest Updates

- Rebranded platform naming to Trust Net across user-facing project docs and frontend metadata.
- Added and refreshed module-level documentation across frontend, gateway, shared package, services, and model package.
- Documented the synchronous image analysis path via `/scans/analyze` and async scan pipeline paths (`/scans/upload`, `/scans/text`, `/scans/url`).
- Captured current trust engine behavior (Kafka-driven fusion with in-memory score repository in the current implementation).
- Consolidated local run and test flows with launch scripts and service-level test commands.

## What Is In This Repository

- Frontend workstation: React + Vite UI for scan workflows and report viewing.
- Gateway: FastAPI reverse proxy and auth/rate-limit perimeter.
- Services:
  - Auth service for registration/login/JWT lifecycle.
  - Scan management service for intake, validation, storage, and dispatch.
  - Image deepfake service for synchronous and Kafka-driven inference.
  - Trust engine for result fusion and trust-risk scoring.
- Shared package: cross-service constants, schemas, auth helpers, and logging.
- Model package: reusable image-deepfake forensic detectors.

## Architecture At A Glance

1. Client sends requests to gateway at <http://localhost:8000>.
2. Gateway proxies auth endpoints to Auth Service and scan endpoints to Scan Management Service.
3. Scan Management supports:
   - Direct synchronous image analysis via /scans/analyze.
   - Async scan creation (/scans/upload, /scans/text, /scans/url) with Kafka event dispatch.
4. Frontend uses gateway-first integration and includes a fallback direct detector path to the image service (`/detect/file`) when gateway analyze is unavailable.
5. Image Deepfake Service consumes detection.requested.image_deepfake when Kafka consumer is enabled.
6. Trust Engine consumes detector.*.completed topics and computes fused trust scores.

## Local Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop (for Kafka and optional infra services)

## Quick Start

### 1. Create and activate virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
python -m venv .venv
.\.venv\Scripts\activate.bat
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install backend dependencies

Recommended one-step installer from the repository root:

```powershell
.\install-deps.bat
```

Or run the PowerShell script directly:

```powershell
.\install-deps.ps1
```

Manual install sequence, if you prefer to run the commands yourself:

```powershell
pip install -e shared/
cd services/auth
pip install -r services/auth/requirements.txt
cd ..\scan_management
pip install -r services/scan_management/requirements.txt
cd ..\image_deepfake
pip install -r services/image_deepfake/requirements.txt
cd ..\trust_engine
pip install -r services/trust_engine/requirements.txt
cd ..\..
cd gateway
pip install -r gateway/requirements.txt
cd ..
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Start services

Windows one-click launcher:

```powershell
.\start-dev.bat
```

Cross-platform scripts:

```powershell
.\start-dev.ps1
```

```bash
chmod +x start-dev.sh
./start-dev.sh
```

Manual start option:

1. `docker compose up -d kafka`
2. `uvicorn gateway.app.main:app --port 8000 --reload`
3. `uvicorn services.auth.app.main:app --port 8001 --reload`
4. `uvicorn services.scan_management.app.main:app --port 8002 --reload`
5. `uvicorn services.image_deepfake.app.main:app --port 8003 --reload`
6. `uvicorn services.trust_engine.app.main:app --port 8004 --reload`
7. `cd frontend && npm run dev`

## Service Endpoints

- Frontend: <http://localhost:5173>
- Gateway docs: <http://localhost:8000/docs>
- Gateway health: <http://localhost:8000/health>
- Auth health: <http://localhost:8001/health>
- Scan Management health: <http://localhost:8002/health>
- Image Deepfake health: <http://localhost:8003/health>
- Trust Engine health: <http://localhost:8004/health>

## Module Documentation

- [frontend/README.md](frontend/README.md) - Frontend app stack, API integration, build and run.
- [gateway/README.md](gateway/README.md) - Gateway routing, middleware, configuration, and tests.
- [shared/README.md](shared/README.md) - Shared schemas, constants, auth helpers, and utilities.
- [services/auth/README.md](services/auth/README.md) - Auth API, token lifecycle, configuration, tests.
- [services/scan_management/README.md](services/scan_management/README.md) - Intake, validation, storage, and Kafka dispatch.
- [services/image_deepfake/README.md](services/image_deepfake/README.md) - Direct detection endpoints and Kafka worker mode.
- [services/trust_engine/README.md](services/trust_engine/README.md) - Fusion API, Kafka consumer, trust score pipeline.
- [models/image_deepfake/README.md](models/image_deepfake/README.md) - Reusable detector package and forensic modules.

## Testing

Run all configured tests:

```bash
python -m pytest -v
```

Run by area:

```bash
python -m pytest gateway/tests -v
python -m pytest services/auth/tests -v
python -m pytest services/scan_management/tests -v
python -m pytest services/image_deepfake/tests -v
python -m pytest services/trust_engine/tests -v
python -m pytest models/image_deepfake/tests -v
python -m pytest shared/tests -v
python -m pytest tests/e2e -v
```

## Repo Structure

- `frontend/` - React workstation
- `gateway/` - API gateway
- `services/` - backend microservices
- `models/image_deepfake/` - reusable image forensic model package
- `shared/` - shared contracts and utilities
- `benchmark/` - benchmark and evaluation scripts
- `docs/` - architecture and technical documentation
- `start-dev.bat`, `start-dev.ps1`, `start-dev.sh` - local launch scripts

## Notes

- Default local DBs for auth and scans are SQLite files in repo root (`auth_dev.db`, `scan_dev.db`).
- Kafka publish/consume logic includes fallback behavior when broker is unavailable.
- Frontend includes offline/auth mock fallback paths for development.
