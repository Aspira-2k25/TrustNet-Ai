# Team setup

> **Quick Setup Guide**: For standalone modular scripts (`setup-phishing.bat`, `setup-scam.bat`) and the model file sharing guide, see the [Complete Team Handoff & Setup Manual](TEAM_HANDOFF_AND_SETUP_GUIDE.md).

Run commands from the cloned **TrustNet-Ai** repository. Use Windows PowerShell.

## Requirements

- Python **3.11** (`py -3.11 --version`).
- Node.js **24 LTS** recommended; this checkout was checked with **24.13.0**. Vite 8 requires a compatible modern Node runtime; do not use Node 18.
- Git; Docker Desktop with Linux containers for Kafka/Mongo and optional live phishing collection.
- Existing image environment and Hugging Face model cache, or the project's documented image setup. The phishing installer does not alter the image environment.

## Configuration and model packages

Copy `.env.example` to `.env` **only if `.env` is missing**. Set a private `JWT_SECRET_KEY`; never commit `.env` or share production secrets. For standalone development use:

```dotenv
ENVIRONMENT=dev
ALLOW_MOCK_AUTH=false
DATABASE_URL=sqlite+aiosqlite:///./scan_dev.db
KAFKA_ENABLED=false
PHISHING_SERVICE_URL=http://127.0.0.1:8007
SCAM_SERVICE_URL=http://localhost:8005
SCAM_OPTIONAL_ANALYSIS_ENABLED=false
GROQ_API_KEY=
```

Keep an existing working `.env`. Environment values supplied by launchers override defaults. Do not replace existing databases or Docker volumes.

Git contains model configs and installers, **not the large weights**. Obtain these releases from the project owner:

1. Scam: `TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip`, put in `exports/`; or restore the complete checksummed `models/scam_message/artifacts/` bundle. A single weights file still requires the tracked tokenizer/config files.
2. Phishing: `TrustNet-Phishing-regional-recall-v1.zip`, put in `exports/`.

The phishing manifest SHA-256 is `30407968c6d02ab076db933a74201d7ac29853637e2d98d2a0faed897a8c6a9c`. The installer validates that pinned manifest and all eight component SHA-256 values **before loading joblib models**. Do not load untrusted replacement packages. The ZIP checksum is supplied alongside owner-distributed packages; component verification is authoritative for this selected release. No Git LFS or teammate Hugging Face cache is assumed for scam/phishing.

The image module retains its Hugging Face model and saved preprocessing: `dima806/deepfake_vs_real_image_detection`. A new teammate needs network access for its first model download and an appropriate Hugging Face token if the configured hosted service requires one. Cached local inference uses the same model; never substitute a different checkpoint silently.

## Installation

Existing image/scam users add phishing without changing those environments:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts/setup/install-phishing.ps1
```

This creates `.venv-phishing`, installs its pinned runtime dependencies and safely extracts the selected ZIP. To specify a downloaded ZIP elsewhere:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts/setup/install-phishing.ps1 -Package "D:\Downloads\TrustNet-Phishing-regional-recall-v1.zip"
```

For a fresh workstation, use ` .\setup.bat ` after installing prerequisites and placing both packages in `exports/`. It installs the main, scam and isolated phishing runtimes plus frontend dependencies. To finish scam setup separately use ` .\scripts/setup/setup-scam.bat `. Frontend manual installation is `cd frontend`, `npm ci`, then `cd ..`.

An existing main/image `.venv` is preserved by `setup.bat`. Internal setup and checks now live under `scripts/`; follow the paths in this guide if an older model ZIP contains an earlier setup note. The model release and checksums are unchanged.

Verify artifacts:

```powershell
.\.venv-scam\Scripts\python.exe .\scripts/checks/verify-scam.py
.\.venv-phishing\Scripts\python.exe .\scripts/packaging/package-phishing-team.py --verify
```

## Start and stop

```powershell
.\start-dev.bat
```

The launcher starts phishing first, then scam/auth/scan/gateway, then image/trust/frontend. Website: **http://localhost:5173**. Ports: gateway 8000, auth 8001, scan 8002, image 8003, trust 8004, scam 8005, phishing 8007, frontend 5173.

With Docker ready, it starts Kafka/Mongo and the phishing worker/isolated collector; queued URL scans use Kafka. Without Docker, offline local phishing inference and message/link fusion still work; missing live DNS/TLS/page/reputation checks are disclosed. PostgreSQL, Redis and MinIO are infrastructure options; local development can use SQLite/local uploads. ORM tables are created at startup; do not reset databases for setup.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts/checks/check-full-startup.ps1
.\.venv-scam\Scripts\python.exe .\scripts/checks/smoke-message-url.py
.\stop-dev.bat
```

The smoke command makes a real combined inference request and checks gateway authentication. Health checks alone do not prove image inference. Stop local launcher-owned processes only; Docker services and volumes are preserved. To stop the named project containers separately, use `docker compose stop phishing phishing-collector kafka mongodb` with the same Compose overlays used at launch; never use `down -v` to troubleshoot.

## Website and Gmail extension

Try: `Your appointment is confirmed. View your receipt at https://example.com/`. The message result includes separate message/URL scores, combined warning index, link coverage, history and PDF export. Example text is not an accuracy benchmark.

For Gmail in Chrome/Edge:

1. Open `chrome://extensions` or `edge://extensions`; enable Developer mode.
2. Select **Load unpacked**, choose `extensions/trustnet-mail` in the repository.
3. Open extension options, choose `http://localhost:8000` and sign in with your TrustNet account.
4. Reload Gmail, open one non-private test email, expand its body and click **Scan Message**.

Only the selected expanded message and its displayed destination links are submitted when requested. Tokens remain in trusted extension session storage; passwords are not retained. Reload the extension and Gmail after pulling extension changes. Live Gmail testing depends on the browser session; DOM/service-worker fixture tests are not proof of a live Gmail installation.

Website and extension message results offer **Inspect this URL** for each supported saved link. This separately contacts the destination through the protected backend collector and shows timestamped domain, IP, TLS and static HTML observations, model assessment and unavailable checks. It does not execute JavaScript or overwrite the original quick score. Snapshots persist in history and message PDF exports. The existing database startup adds `link_inspections` automatically; no database reset is needed. After starting all services, run `.\.venv-scam\Scripts\python.exe scripts/checks/verify-integration.py --inspect --require-live` to require actual live collection in the integration smoke check.

## Optional provider and troubleshooting

Groq is optional. Set `SCAM_OPTIONAL_ANALYSIS_ENABLED=true` and backend-only `GROQ_API_KEY` for an opt-in evidence summary. Local inference works without it; provider errors do not change the local result.

- **Missing weights/checksum mismatch:** rerun the appropriate installer with the complete selected ZIP. Do not edit manifests to bypass verification.
- **Port occupied:** inspect `Get-NetTCPConnection -State Listen`; stop the process with its own launcher. Do not kill arbitrary processes by port.
- **Docker MongoDB port conflict:** the launcher preserves native MongoDB and selects 27018; set `MONGO_HOST_PORT` to another free port if needed.
- **Phishing unavailable:** inspect `runtime-logs/phishing.err.log` or `docker logs` for the named phishing container. `/ready` on port 8007 must return 200; `/health` is liveness only.
- **Kafka/collector unavailable:** message scans retain available text evidence and explicitly mark missing URL coverage. Local fallback can run with Docker off.
- **Image issue:** retain `.venv`, model cache and label mapping; inspect actual result analyzer statuses. LM Studio is optional for fast image scans.
