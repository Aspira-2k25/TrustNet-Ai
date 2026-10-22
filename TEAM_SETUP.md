# TrustNet AI: teammate setup (Windows, CPU)

## What the maintainer must send

1. Repository access and branch `IMGURLMSG_TEST`.
2. `exports/TrustNet-Phishing-regional-recall-v1.zip` and its `.zip.sha256` file, through your private team file share. The ZIP is 2,993,917 bytes. Expected SHA-256: `90999299b28a9b04927d848f0f4a6aefd8309a4be7f66bf9a78ccf840d84ff27`.

Do **not** send your real `.env`, HF/Groq keys, JWT secret, virtual environments, databases, uploaded images, emails or scan history. Every teammate creates a local configuration and account. Public model downloads need internet, but normal local inference needs no paid API or GPU. No Git LFS is required.

## 1. Install prerequisites

Install Git, Python **3.11** (verified 3.11.9), Node **24 LTS** (verified 24.13.0, includes npm), and Windows PowerShell 5.1 or newer. Prefer 16 GB RAM and several GB free disk space. Docker Desktop is optional for synchronous scans; it enables queued jobs and the isolated live website collector. Keep Docker running if using that functionality.

```powershell
py -3.11 --version
node --version
npm --version
git clone --branch IMGURLMSG_TEST https://github.com/Aspira-2k25/TrustNet-Ai.git
cd TrustNet-Ai
```

For an existing clone, first save your own work, then:

```powershell
git fetch origin
git switch IMGURLMSG_TEST
git pull --ff-only
```

Do not reset or discard local changes to resolve a failed pull.

## 2. Install the project

Create `exports/` inside the repository and place the phishing ZIP and checksum there. Verify the ZIP:

```powershell
Get-FileHash .\exports\TrustNet-Phishing-regional-recall-v1.zip -Algorithm SHA256
.\setup.bat
.\setup.bat --verify
```

Compare the hash with the value above. Setup creates `.venv`, `.venv-scam` and `.venv-phishing`, installs their pinned requirements, installs frontend dependencies with `npm ci`, verifies the phishing components and downloads pinned image weights. Keep these environments separate. Existing valid artifacts are reused.

Use `.\setup.bat --check` to check Python/Node/npm prerequisites without installing packages or starting services. Setup and launch use the repository's own paths, so another Windows username or a folder with spaces is supported. No global Python packages, global Vite or globally installed project utilities are required. Git, Python, Node/npm and PowerShell themselves must be installed and discoverable. The launch scripts check Python 3.11 environments instead of silently accepting another version. These entry points are for Windows; Linux/macOS support is not claimed.

Git provides the selected message model in `models/scam_message/multilingual_artifacts`, tokenizer/configuration files, thresholds, experimental image head, pinned certificate trust anchors and artifact installers. It does not provide the large image weights or phishing checkpoint bundle. Image setup downloads the selected CommunityForensics ViT (87,270,764-byte weight) and TruFor (281,496,429-byte weight), verifies their pinned hashes and stores them in the repository's ignored artifact directories. A teammate's Hugging Face cache is not required. The optional legacy DistilBERT package is **not** needed for the default message model.

**Licence limits:** TruFor is restricted to informational/nonprofit use, and the experimental image head has noncommercial data restrictions. Review `models/image_deepfake/MODEL_CARD.md` and `models/image_deepfake/vendor/trufor/LICENSE.txt` before deployment. Dataset/model terms for message and URL artifacts also apply. This is not an unrestricted commercial distribution.

## 3. Configure safely

Setup creates `.env` from `.env.example` when absent and initializes a random local JWT secret. Keep `.env` private. Do not copy a teammate's JWT secret. Leave these defaults for local use:

```dotenv
ALLOW_MOCK_AUTH=false
SCAM_TEXT_POLICY=multilingual
SCAM_OPTIONAL_ANALYSIS_ENABLED=false
GROQ_API_KEY=
HUGGINGFACE_API_KEY=
HF_DEEPFAKE_MODEL=buildborderless/CommunityForensics-DeepfakeDet-ViT
IMAGE_LOCALIZER_BACKEND=trufor
STORAGE_DIR=./storage_uploads
VITE_API_GATEWAY_URL=http://localhost:8000
```

The template's `JWT_SECRET_KEY=GENERATE_ON_SETUP` is a placeholder, not a usable shared credential. `scripts/setup/init-env.py` replaces it locally. Downstream URLs and ports are in `.env.example`. Leave `DATABASE_URL` unset to use separate local SQLite auth/scan databases. Tables are initialized at startup; no manual migration is required for the current local schema. PostgreSQL, Redis, S3/MinIO, Grafana and ELK are not required for this flow. Never delete databases or Docker volumes as a setup fix.

Optional Groq: supply your own backend `GROQ_API_KEY`, set `SCAM_OPTIONAL_ANALYSIS_ENABLED=true`, and explicitly opt into optional scan analysis. This is not needed for local detection. Provider failure must not mean safe. Never put a secret in a `VITE_` variable. The HF token is optional for the pinned public model downloads; no hosted paid inference is required.

## 4. Start, check and stop

From the repository root in a normal terminal:

```powershell
.\start-dev.bat
```

Open **http://localhost:5173/**, register your own local account and sign in. The launcher starts URL inference, authentication, message inference, scans, gateway, image inference, trust service and frontend. If Docker is available, it also prepares optional Kafka/Mongo/collector infrastructure. Local ports: gateway 8000, auth 8001, scans 8002, images 8003, trust 8004, messages 8005, URLs 8007, frontend 5173.

For a deterministic local launch that skips Docker even when Docker Desktop is running, use `.\start-dev.bat --offline`. Message, link-model and image inference still run locally; live website collection and queued worker features are unavailable in this mode. The flag does not stop containers already running.

One smoke command checks readiness and performs real inference:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\checks\check-full-startup.ps1
```

Try Message with `Send your OTP and UPI PIN to claim your lottery prize.` Try a harmless message with a link: `Your appointment is tomorrow. Details: https://example.com/`. Message links are sent to the URL branch. These are functional examples, not accuracy benchmarks. Open history, reopen the result and download its PDF. Failed or unavailable checks should remain visibly incomplete.

```powershell
.\stop-dev.bat
```

Stop removes only matching launcher-owned processes. It preserves databases, uploads and Docker containers/volumes. Stop this project's optional containers in Docker Desktop if needed; do not use `down -v`.

## 5. Install the Gmail extension once

Start the project first. In Chrome, Edge or Brave, open the extensions page, enable Developer mode, choose **Load unpacked**, then select `extensions/trustnet-mail/`. Source runtime files are directly loadable. Open the extension settings, keep the local gateway URL and connect using your own TrustNet account. Open Gmail and explicitly click the TrustNet scan control on the message you choose to check. Nothing should scan automatically. Suspicious URLs are plain text. Use **Open full report** for the saved website report. Reconnect if login expires; reload the extension from the browser extensions page after pulling changes. Firefox/Safari support is not claimed. Automated tests cover the supported flow; live Gmail behavior still needs manual acceptance testing.

To test/build the extension:

```powershell
cd extensions\trustnet-mail
npm ci
npm test
npm run build
cd ..\..
```

The build also produces `extensions/trustnet-mail/dist/trustnet-mail`, which can be loaded unpacked instead of the source folder. Install only one copy.

## 6. Development checks

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/test.txt
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm test
npm run build
npm run lint
cd ..
```

These checks do not certify universal image/scam detection. Signed origin, pixel-model evidence, edit localization and diagnostic plots have different meanings. Authenticity claims are disabled in the current image profile; invisible proprietary watermark decoding and visible-logo recognition are not implemented. See each module's `MODEL_CARD.md` for measured results and limitations.

## Troubleshooting and team updates

* Missing phishing model: put the exact ZIP in `exports/`, then run `.\setup.bat --phishing`. Do not load arbitrary untrusted pickle/joblib files.
* Missing image weights: run `.\.venv\Scripts\python.exe scripts/setup/install-image.py` and then `.\.venv\Scripts\python.exe scripts/setup/install-image-localizer.py`. Run `.\setup.bat --verify` afterwards. Internet/download restrictions may require retrying; never bypass checksums.
* Image edit timeout: the AI check and edit check are separate. A timed-out edit check cannot supply a reliable mask. CPU timeouts or unsupported image modes are not evidence that the image is real.
* Backend offline: inspect `runtime-logs/`, run the smoke command and resolve the first failing service. Extension login needs the gateway and auth service. Use localhost consistently.
* Port already occupied: run `.\stop-dev.bat`; if still occupied, identify the owning application. Do not kill unrelated services by port.
* Docker unavailable: ordinary synchronous local scans can run, but live website inspection/worker features may be unavailable. Those results must not be called safe.
* After `git pull --ff-only`, rerun setup when dependencies/artifact manifests changed, verify models, restart services and reload the extension. Do not replace your `.env` with someone else's. Keep package ZIPs outside commits, and never commit personal scans or credentials.
