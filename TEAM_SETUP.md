# Teammate setup — scam module

Use **Python 3.11** (tested 3.11.9) and **Node 24** (tested 24.13.0; Vite8 requires20.19+ or22.12+). Git pull provides runtime code, schemas, tokenizer/configuration, calibration, model manifest, frontend source/lockfile, Gmail extension, launch/install/smoke scripts and documentation. It does **not** provide the 267.8 MB transformer weight, compiled frontend, virtual environments, databases, secrets or another person's Hugging Face cache.

Ask the repository owner for **TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip** and its checksum, created in `exports/`. Version/SHA256/file checksums are committed in `models/scam_message/model-package.json`. This selected fine-tuned model is not downloadable from the generic SST2 model ID. No Git LFS or paid API is needed. Model/data-license attribution is supplied in `docs/scam-portable`. Alternatively use the complete portable ZIP, which includes weights and the built website.

## Fresh scam-only checkout

Run in the pulled repository root. These commands create an independent CPU environment; they do not upgrade the image environment.

```powershell
py -3.11 .\install-scam-model.py --package 'C:\path\to\TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip'
powershell -ExecutionPolicy Bypass -File .\install-scam.ps1
.\.venv-scam\Scripts\python.exe .\verify-scam.py
Push-Location frontend
npm ci
npm run build
npm run lint
Pop-Location
powershell -ExecutionPolicy Bypass -File .\start-scam.ps1 -Portable
py -3.11 .\scripts\smoke-scam.py
Start-Process http://localhost:5173
```

`-Portable` also works from a checkout after building frontend/dist: it starts scam8005, auth8001, scan8002, gateway8000, then compiled website5173. Fresh setup automatically generates a random backend JWT secret and `.env`; auth and scans share `portable-state.sqlite`. SQLAlchemy startup creates existing auth/scan tables plus additive `scan_assessments`; there is no destructive migration and no required PostgreSQL/Redis/Mongo/Kafka for synchronous scam scans. Register a local account on the website, sign in, select SMS/Email and paste a message. History stores the complete canonical message/result. Stop with `powershell -ExecutionPolicy Bypass -File .\stop-scam.ps1`; preserve `.env` and SQLite on restart.

Example input: `Your appointment is confirmed for tomorrow at 10 AM.` Email example: subject `Member newsletter`, body `Save 20% this weekend. Browse your usual shop. Unsubscribe if you no longer want updates.` Examples show usage, not benchmark accuracy. For a real authenticated API request use the PowerShell login/Bearer example in `docs/scam-portable/README.md`.

## Existing full application/image environment

The owner should keep the existing `.env`, image `.venv`, image artifacts/cache and original database configuration. For the full local website, run `.\start-dev.bat` from the repository root: it checks all ports, starts the separate scam/auth/scan/gateway environments with backend readiness checks, then launches the original image API, trust engine and frontend in terminals. Normal synchronous mode needs no Docker; asynchronous deployment is separate. Close the three visible terminals with Ctrl+C and run `.\stop-scam.ps1` to stop background services. Do not combine this launcher with the manual commands below. Run install-scam and model verification, then `powershell -ExecutionPolicy Bypass -File .\start-scam.ps1` **without** `-Portable`. The scanner uses the existing image `.venv`; auth/gateway/scam use `.venv-scam`. In another terminal: `cd frontend; npm ci; npm run dev`. Other detector services use the project's existing startup/environment setup and are outside this scam launcher. This preserves rather than replaces the image model.

Fresh teammates wanting full image detection must separately provision the existing image service's documented requirements/artifacts and authorized Hugging Face access. The deployed model ID is `dima806/deepfake_vs_real_image_detection`, recorded cache revision `29e4cf9efc543845610045f6ba7e88e5cf9d9301`; do not substitute a different model or assume another user's cache exists. Image dependencies were not upgraded by this work. On the current owner machine Windows Application Control blocks the existing `_regex` DLL, affecting ViT/HF tests; do not interpret that as a successful image assessment. Comparable labelled image accuracy was not established.

## Configuration

Fresh scam-only `.env` uses `ENVIRONMENT=dev`, `ALLOW_MOCK_AUTH=false`, a random `JWT_SECRET_KEY`, `KAFKA_ENABLED=false`, `SCAM_OPTIONAL_ANALYSIS_ENABLED=false`, blank `GROQ_API_KEY`, `GROQ_MODEL=openai/gpt-oss-20b`. Existing checkout `.env.example` describes full infrastructure with placeholder PostgreSQL credentials; do not blindly copy that configuration for the SQLite-only setup. All services must share the same JWT secret. Launcher sets `DATABASE_URL` to its local SQLite in Portable mode. `SCAM_SERVICE_URL=http://localhost:8005`, scanner timeout35s, local inference timeout20s/concurrency2. Never place keys in VITE variables, frontend, extension or commits.

Optional Groq: configure `GROQ_API_KEY` locally and set `SCAM_OPTIONAL_ANALYSIS_ENABLED=true`, restart, then explicitly opt in per website scan. Only bounded evidence fragments/notes leave the machine. This only orders existing evidence, does not improve/change classification, and has graceful timeout/429/schema failure fallback. Local detection needs no key. No paid/live Groq verification was performed.

## Extension

Chrome `chrome://extensions` / Edge `edge://extensions`: Developer mode →Load unpacked →`extensions/trustnet-mail`. In Options select fixedlocalhost8000, sign in with the local TrustNet account, reload Gmail, open/expand one message and clickTrustNetScan. Reconnect after token expiry/browser restart. No inbox autoscan. Gmail adapter/MV3/navigation fixtures and real gateway communication passed; live browser installation/Gmail DOM remains unverified. Outlook Web: manual website paste only. See extension README.

## Troubleshooting and measured limits

Missing/checksum-invalid weights: install the exact model ZIP then run verify-scam; generic HF base weights are incompatible. Service503: inspect runtime-logs/*.err.log and `/ready`; never treat unavailable as safe. Ports8000/8001/8002/8005/5173 occupied: reuse existing services or stop their own launcher; do not kill unrelated processes. Do not rebuild a ZIP while its extracted model is memory-mapped/running. Dependency installer includes SQLAlchemy asyncio/greenlet and CPU PyTorch; no image environment changes.

Local scans are independent of Docker/Kafka. Async `/scans/text` requires configured Kafka/worker/completion consumer; genuine broker ACK, replay/DLQ/commit/persistence/failure transitions were tested on a separate local Docker broker19094. Full multi-service Docker deployment remains unverified.

Selected model `message-distilbert-lexical-links-hybrid-4`: frozen 577-message macro-F1 0.9647, fraud threshold recall 95.65%, covered operational recall 94.98%, ham alerts 0/200 (95% upper bound 1.88%). This is limited collection evidence, not field accuracy. The older independent-source diagnostic macro-F1 remains 0.5561 versus baseline 0.5941 (worse), despite recall gains. Long mixed-content fraud can be missed; modern promotion false positives remain insufficiently evaluated. Sender unverified, AI authorship not assessed. Full tables: `docs/scam-portable/evaluation.json`; details: `docs/SCAM_RESEARCH_EVIDENCE.md` and model card.

Rollback: retain the separate original `TrustNet-Scam-Model-sms-distilbert-linear-hybrid-2.zip` if needed. Stop the launcher, run `py -3.11 .\install-scam-model.py --baseline --package 'C:\path\to\TrustNet-Scam-Model-sms-distilbert-linear-hybrid-2.zip'`, then restart. The version-2 archive has its own checksummed `rollback-package.json`; it is not the selected model package.

Before pushing review the changed API/shared/persistence/frontend/PDF/image-test files and new model/extension/startup assets. `.gitignore` excludes secrets, environments, data/state, large weights and exports. Share the model ZIP separately; no commit/push/upload was performed by the agent.

