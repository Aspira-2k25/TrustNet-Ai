# Scam message service

Current selected runtime is `message-distilbert-lexical-links-hybrid-4`. Prefer [TEAM_SETUP.md](../../TEAM_SETUP.md) for the selected-model package installer, complete CPU dependency installation and readiness-checked startup. [Continuation verification](../../docs/SCAM_CONTINUATION_HANDOFF.md) supersedes historical first-stage Docker/Kafka availability notes below. Email input, separate output dimensions, real-predictor signed attribution and optional backend Groq are implemented; limited collection-specific email calibration/evaluation is available; modern inbox reliability and live Gmail installation remain unverified. Groq is disabled by default, per-scan opt-in is required and it only orders bounded existing evidence IDs without changing predictions. See [official structured-output documentation](https://console.groq.com/docs/structured-outputs); no paid/live provider calls were made.

Local English SMS/email screening: separate ham, unsolicited spam and smishing classes. The selected calibrated DistilBERT/linear hybrid uses local safetensors and JSON/NPZ artifacts. Datasets, notebooks, a cloud provider and the sibling research folder are unnecessary for local inference. Separate-source performance remains limited and is reported explicitly. See [model card](../../models/scam_message/README.md).

## Windows setup

Run from the repository root. Preserve the existing image `.venv`.

```powershell
# Use the existing Python 3.11 executable to create an independent environment.
& .\.venv\Scripts\python.exe -m venv .venv-scam
& .\.venv-scam\Scripts\python.exe -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
& .\.venv-scam\Scripts\python.exe -m pip install -r services/scam_message/requirements.txt -e ./shared
$env:KAFKA_ENABLED = 'false'
& .\.venv-scam\Scripts\python.exe -m uvicorn services.scam_message.app.main:app --host 127.0.0.1 --port 8005
```

In separate terminals from the repository root, use your existing configured environment:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn gateway.app.main:app --port 8000
& .\.venv\Scripts\python.exe -m uvicorn services.auth.app.main:app --port 8001
& .\.venv\Scripts\python.exe -m uvicorn services.scan_management.app.main:app --port 8002
# Frontend terminal:
Set-Location frontend
npm install
npm run dev
```

The scan-management service retains its existing image inference dependencies. On a fresh installation install its requirements and `-e ./shared` in the existing application's intended environment; this implementation did not upgrade the working image environment. `start-dev.ps1` issues background launch commands for the application and starts scam inference when `.venv-scam` exists. Check health independently; a launched process is not proof of readiness. `docker compose up -d` starts infrastructure only.

`GET http://localhost:8005/health` reports service liveness. `/ready` returns 503 for missing/corrupt artifacts, otherwise model version. Diagnostic internal endpoint:

```powershell
$body = @{ scan_id = 'diagnostic-001'; text = 'Your OTP is 482193. Do not share it with anyone.' } | ConvertTo-Json
Invoke-RestMethod http://localhost:8005/infer -Method Post -ContentType application/json -Body $body
```

The browser goes through the Gateway: `POST /api/v1/scans/scam/analyze` with `{"text":"..."}` and the existing access-token convention. Scan management calls `/infer`, verifies scan/module/status, and atomically saves the full message/result/trust score to the existing scan database plus an additive `scan_assessments` table. `GET /api/v1/scans/{id}` and list return these results after restart. Existing scans without historical results remain unavailable; their missing evidence cannot be reconstructed.

## Settings and failure semantics

Settings read `.env` and process environment from the working directory:

| Setting | Default / role |
|---|---|
| `SCAM_SERVICE_URL` | scan management: `http://localhost:8005` |
| `SCAM_SERVICE_TIMEOUT_SECONDS` | scan management: 35 seconds, including optional provider timeout |
| `SCAM_MAX_CONCURRENCY` | inference: 2 active threads, max configurable 8 |
| `SCAM_TIMEOUT_SECONDS` | inference: 20 seconds |
| `KAFKA_ENABLED` | scan management and scam: false |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` |
| `WORKER_STATE_DIR` | durable worker deduplication SQLite directory: `./runtime_state` |
| `MAX_IMAGE_SIZE_MB` | scan management / image service / validator: 10 |
| `MAX_AUDIO_SIZE_MB`, `MAX_VIDEO_SIZE_MB` | scan management: 25 / 200 |

Scam text accepts 1–10,000 Unicode codepoints, rejects whitespace/NUL, unsupported scripts and recognized Hinglish patterns. Latin script alone cannot reliably detect language. Long accepted text is processed in full; modern inbox accuracy is not established. Busy inference returns 429, timeout 504, model/service unavailable 503, unsupported input 422. Timed-out work occupies its bounded slot until the actual thread finishes; no unbounded work queue. Failed inference is never a completed low-risk scan. Failure to save a result returns 503 instead of claiming it was saved. Rate limiting at the Gateway returns 429. `/api/v1/scans/limits` supplies authenticated frontend upload configuration.

## Optional Kafka

Start a real broker, set `KAFKA_ENABLED=true` in scan management and scam, and restart both. Image service separately reads its existing `ENABLE_KAFKA_CONSUMER` flag. Use the same bootstrap endpoint and durable worker state storage. Canonical topics are `detection.requested.scam_message` and `detector.scam_message.completed`; image uses its canonical equivalents. Scan completion consumer persists results. Producer sends are awaited with bounded retries; consumers commit offsets after successful durable handling/publication. Identical request retries reuse the SQLite-cached completion, conflicting retries go to `.dlq`. Completion persistence uses first-completion-wins; unknown scans or wrong module/key/topic are rejected. Requests are QUEUED, then SUCCESS/PARTIAL_SUCCESS/FAILED on completion; no fabricated processing-stage progress is emitted. Dispatch failure is persisted FAILED and returns 503. Synchronous image/scam inference works with Kafka disabled.

Actual Docker Kafka integration now passed on an isolated localhost19094 broker: publication ACK, worker processing, complete persistence, replay, conflicting/invalid DLQ, manual commits and FAILED/UNKNOWN/null score handling. Separate earlier fixture tests are not substituted for this evidence. Crash recovery under arbitrary broker outages remains unverified. The separate trust-engine aggregation repository remains in memory; scan history persistence is the database-backed path described above.

## Docker

Build with repository-root context:

```powershell
docker build -f services/scam_message/Dockerfile -t trustnet-scam .
```

Analogous root-context Dockerfiles were repaired for gateway/auth/scan management. Docker daemon is now available and the isolated broker was exercised; full application image builds/deployment were not executed. A scam container must be reached by scan management through `SCAM_SERVICE_URL` on the container network; localhost refers to that container. Existing JWT/auth/role conventions are unchanged.
