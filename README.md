# TrustNet AI

A research application for checking images, messages and website links, with explanations, private scan history, PDF export and a Gmail extension. Results are indicators, not proof.

## Windows setup

Use Python **3.11** (verified 3.11.9), Node **24 LTS** (verified 24.13.0), npm and Windows PowerShell 5.1 or newer. CPU inference works without a GPU or API key. Allow several GB of disk space and preferably 16 GB RAM. Docker Desktop is optional for synchronous scans; it enables Kafka, MongoDB and the isolated live website collector.

From the repository folder:

```powershell
.\setup.bat
.\start-dev.bat
```

Open **http://localhost:5173/**. Register a local account, sign in and choose Image, Message or URL. A harmless sample message is `Your appointment is tomorrow at 10. View details at https://example.com/.` To check an explicit warning, use `Send your OTP and UPI PIN to claim your lottery prize.` These are smoke examples, not accuracy tests.

Stop launcher-owned local processes with `.\stop-dev.bat`. Docker containers and volumes are intentionally preserved. To stop optional infrastructure without removing data, use Docker Desktop to stop only this project's Kafka, MongoDB, phishing and collector containers. Do not use `down -v` to troubleshoot.

### Model distribution

Git contains inference code, selected small configuration files, tokenizer/configuration files, thresholds, the experimental feature head, vendor licences, installers and package checksum manifests. **Git does not contain the large image/scam weights or the selected phishing bundle. No Git LFS is required.**

Before first setup, obtain these existing research artifacts from the project maintainer and put them in `exports/`:

| Package | Size | Verification |
| --- | ---: | --- |
| `TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip` | 248,559,032 bytes | SHA-256 in `models/scam_message/model-package.json` |
| `TrustNet-Phishing-regional-recall-v1.zip` | 2,993,917 bytes | Included SHA-256 file; pinned manifest plus all eight component hashes are checked by the installer |

Scam package SHA-256: `1e499d55a042ee7268d6a49da91d81e60f1c776a936d675b92575fdbc4e50623`.

`setup.bat` downloads the image ViT from the pinned Hugging Face revision in `models/image_deepfake/calibration/global-artifacts.json` (87,270,764-byte weight). It also installs the official TruFor weight (about 261 MB) using the pinned URL and SHA-256 in its vendor manifest. Neither installer requires a pre-existing Hugging Face cache. Existing valid artifacts are reused.

**Research licensing:** TruFor permits informational/nonprofit use and prohibits unauthorised profit-oriented/industrial use. See `models/image_deepfake/vendor/trufor/LICENSE.txt`. The experimental modern feature head uses SafeIMG CC BY-NC-SA 4.0 data and is limited to academic/noncommercial use. The ViT itself is MIT licensed. Dataset/model source terms still apply to scam and phishing artifacts; no blanket commercial licence is asserted. Raw datasets are not redistributed. For commercial work, replace restricted components and obtain appropriate rights.

The localizer implements a swappable interface. Set `IMAGE_LOCALIZER_BACKEND=none` to disable it. Missing localization yields explicit limits, never an authenticity claim.

### Environment and persistence

Setup creates `.env` from `.env.example` only when absent. Keep `ALLOW_MOCK_AUTH=false`. The launcher generates a local JWT secret when needed; keep the same secret across gateway/auth/scan services. Never share a real `.env` or commit credentials.

Local defaults use existing SQLite development databases and `STORAGE_DIR=./storage_uploads`. Tables are created at service startup; no manual migration is required for the current SQLite schema. Do not delete a database to fix startup. Docker Kafka/Mongo are required only for the optional worker path; native Mongo on its normal port is preserved by the infrastructure helper. PostgreSQL, Redis, MinIO, Kubernetes, Grafana and ELK are not required for the documented local flow.

Useful variables are `SCAM_SERVICE_URL`, `PHISHING_SERVICE_URL`, `IMAGE_SERVICE_URL`, `VITE_API_GATEWAY_URL`, `KAFKA_ENABLED`, `KAFKA_BOOTSTRAP_SERVERS`, `IMAGE_LOCALIZER_BACKEND`, `DATABASE_URL`, `STORAGE_DIR` and `JWT_SECRET_KEY`. The services use separate SQLite defaults unless DATABASE_URL is configured. The launcher sets Kafka values. Keep the safe local examples in `.env.example`; use real HTTPS and separate secrets before any public deployment.

Groq is optional, disabled by default. Local inference works without it. To opt into its bounded evidence-ordering feature, configure backend `GROQ_API_KEY` and `SCAM_OPTIONAL_ANALYSIS_ENABLED=true`, then explicitly enable optional analysis for the scan. Provider failure must not turn into a safe verdict or change detector scores. No key belongs in frontend variables.

### Startup and smoke check

The launcher starts optional infrastructure, phishing inference, auth/scam/scan/gateway, then image/trust/frontend. Local ports are 8000 gateway, 8001 auth, 8002 scans, 8003 images, 8004 trust, 8005 messages, 8007 phishing and 5173 website.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\checks\check-full-startup.ps1
```

This checks service readiness, performs real message/link inference and checks real image-service inference. It is a smoke check, not an accuracy benchmark.

If setup fails, fix that error before starting. Missing image weights: run `.\.venv\Scripts\python.exe scripts/setup/install-image.py`, then `install-image-localizer.py` from the same folder. Missing scam/phishing models: supply the exact checksummed ZIPs above and rerun setup. An occupied port is reported rather than killed automatically. Use the owning launcher's stop command and inspect `runtime-logs/`. A model-ready response and Kafka-worker-ready response are separate: phishing `/ready` checks inference, `/ready/worker` checks background processing.

## Gmail extension

In Chrome, Edge or Brave, open the browser's extensions page, enable Developer mode, choose **Load unpacked**, and select `extensions/trustnet-mail/`. No build is required. Open its popup, connect to your local TrustNet account and open a test email in Gmail. Use its scan control to send the selected message and links to the local backend. Reload the extension after pulling changes. Do not assume Firefox or Safari compatibility. Automated extension tests exist; live Gmail is not part of automated verification.

## Coverage and interpretation

Image verdicts use separate global AI, provenance, quality and pixel-localization evidence. Original upload bytes are preserved. TruFor localization uses native pixels or bounded overlapping tiles; attention maps and ELA brightness are not presented as ground-truth edits.

**Authenticity verdicts are currently disabled.** Inpainting, generative fill, object removal and face swaps are not reliably covered. The new modern-generator head failed a high-resolution real-photo guard and cannot produce a standalone AI verdict. Weak or uncorroborated evidence returns Inconclusive. An editable AI metadata tag is not verified provenance, and absent metadata is neutral.

The later 4,178-original training refresh was also evaluated and rejected: it increased abstention and real false alerts on the held-out cohorts. Current runtime weights were retained. See the image model card for the measured comparisons, confidence intervals and TGIF localization limitations. JPEG-only ELA, noise and repeated-pattern diagnostics are available as supporting observations. Optional Grad-CAM shows classifier attention on its own model view; it is separate from the pixel-localization mask.

Scam inference retains DistilBERT plus TF-IDF/Logistic Regression, with explicit secret-request/advance-fee/investment warning rules. Hindi/Hinglish classifier coverage remains limited. A small MuRIL comparison performed better overall but had unacceptable benign Hinglish false alerts, so it was not substituted merely to advertise better accuracy. Historical selected-weight measurements in the model card do not measure the changed decision rules.

Message URLs and email destinations are checked by the phishing module. Fusion takes the maximum available branch warning index; it is not a calibrated combined probability. Automatic scans do not open websites. Explicit live inspection is isolated, bounded and SSRF protected. HTTPS, domain age, an IP address or a missing reputation hit alone never establishes safety or phishing.

## Verification and structure

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/test.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv-scam\Scripts\python.exe -m pytest services/scam_message/tests -q
node --test extensions/trustnet-mail/tests/worker.test.cjs
cd frontend
npm ci
npm run build
npm run lint
```

`requirements/runtime.txt` pins the main environment. Scam and phishing keep isolated requirements/environments because their model libraries differ. Backend code lives in `gateway/`, `services/`, `shared/` and `models/`; UI in `frontend/`; operational commands in `scripts/setup`, `scripts/ops`, `scripts/checks` and `scripts/packaging`. Reproducible current evaluation code is in `benchmark/`, with raw data and substantial outputs outside the app in the external `scam/` research workspace. The running application does not require that folder.

See [image model provenance](models/image_deepfake/MODEL_CARD.md), [the runtime architecture](docs/ARCHITECTURE.md), [scam model provenance](models/scam_message/MODEL_CARD.md) and [phishing model provenance](models/phishing_url/MODEL_CARD.md). Historical presentation diagrams are retained as user-authored research deliverables, not evidence that every depicted service is deployed.
