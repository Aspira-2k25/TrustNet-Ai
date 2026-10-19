# TrustNet AI - Complete Team Handoff & Setup Manual

This comprehensive guide covers how to set up, distribute, modularly configure, and examine every component of the **TrustNet AI** project.

---

## 1. Quick Reference: Setup Commands

| Goal | Command | Description |
|---|---|---|
| **Full Setup (Fresh Machine)** | `.\setup.bat` | Sets up main (`.venv`), scam (`.venv-scam`), phishing (`.venv-phishing`), extracts models, installs frontend deps (`npm ci`), and verifies checksums. |
| **Phishing Only** *(Image & Scam already done)* | `.\setup-phishing.bat`<br>*(or `.\setup.bat phishing`)* | Sets up isolated `.venv-phishing`, extracts phishing model, and verifies integrity **without touching** existing `.venv` or `.venv-scam`. |
| **Scam Only** *(Image & Phishing already done)* | `.\setup-scam.bat`<br>*(or `.\setup.bat scam`)* | Sets up isolated `.venv-scam`, extracts scam model, and verifies integrity **without touching** other environments. |
| **Integrity & Checksum Examination** | `.\setup.bat --verify` | Runs checksum and offline inference verification for both scam and phishing models. |
| **Start Development Stack** | `.\start-dev.bat` | Launches backend microservices and frontend dashboard (port 5173). |
| **Stop Development Stack** | `.\stop-dev.bat` | Safely terminates all TrustNet service processes. |

---

## 2. Team Handoff: What to Share with Teammates

### What is in Git (Repository)
- All source code (Gateway, Services, Frontend, Extensions, Models inference code, Tests, Automation scripts).
- Model manifests, configs, and integrity checkers.
- Requirements and setup scripts.

### What is NOT in Git (Do NOT Commit)
- **Large model weights / artifacts** (stored in `models/*/artifacts` and `checkpoints/`).
- **Virtual environments** (`.venv`, `.venv-scam`, `.venv-phishing`).
- **Private secrets & credentials** (`.env`, private JWT keys).
- **Local databases & uploads** (`*.db`, SQLite files, uploaded images).

---

### The Proper Way to Send Files to Teammates

To onboard a teammate, send them the Git clone URL **plus a secure download link** (e.g., Google Drive or OneDrive) containing the `exports/` folder with the two model ZIP packages:

```
TrustNet-Ai/
└── exports/
    ├── TrustNet-Phishing-regional-recall-v1.zip                           (~40 MB)
    └── TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip (~250 MB)
```

#### Package 1: Phishing URL Model Package
- **ZIP File Name:** `TrustNet-Phishing-regional-recall-v1.zip`
- **Destination Folder:** `exports/TrustNet-Phishing-regional-recall-v1.zip`
- **What it contains:** 8 joblib artifacts + `manifest.json`:
  - `manifest.json` (SHA-256: `30407968c6d02ab076db933a74201d7ac29853637e2d98d2a0faed897a8c6a9c`)
  - `text.joblib`
  - `structural.joblib`
  - `base_fusion.joblib`
  - `base_calibrator.joblib`
  - `complementary_text.joblib`
  - `complementary_fusion.joblib`
  - `correction_fusion.joblib`
  - `correction_calibrator.joblib`
- **Unpacked location:** `models/phishing_url/checkpoints/regional_recall_v1/`
- **Verification Rule:** The installer validates SHA-256 hashes of all 8 files against the signed manifest **before** loading any model.

#### Package 2: Scam Message Model Package
- **ZIP File Name:** `TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip`
- **Destination Folder:** `exports/TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip`
- **What it contains:**
  - `artifacts/model.safetensors` (DistilBERT sequence classification weights)
  - `artifacts/config.json`, `runtime.json`
  - `artifacts/tokenizer.json`, `tokenizer_config.json`, `vocab.txt`, `special_tokens_map.json`
  - `artifacts/hybrid_config.json`, `hybrid_weights.npz`
  - `artifacts/manifest.json`
- **Unpacked location:** `models/scam_message/artifacts/`
- **Verification Rule:** `verify-scam.py` checks file hashes against `manifest.json` and performs an offline test inference.

#### Package 3: Image Deepfake Model (Automatic)
- **Model Name:** `dima806/deepfake_vs_real_image_detection` (Vision Transformer).
- **Handoff:** **No ZIP file needed.** It downloads automatically on first run via Hugging Face and is cached locally.

---

## 3. Step-by-Step Setup Guide

### Prerequisites
1. **Python 3.11** installed:
   ```powershell
   py -3.11 --version
   ```
2. **Node.js 24 LTS** installed (Node 20+ supported; recommended 24.x):
   ```powershell
   node --version
   ```
3. **Git** installed.

---

### Scenario A: Full Project Setup (Fresh Clone)

1. **Clone the repository:**
   ```powershell
   git clone -b futurealok-feature <REPO_URL>
   cd TrustNet-Ai
   ```

2. **Copy the model ZIP files:**
   Place `TrustNet-Phishing-regional-recall-v1.zip` and `TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip` into the `exports/` folder.

3. **Configure Environment Variables:**
   Copy `.env.example` to `.env` (if not already present):
   ```powershell
   if (!(Test-Path .env)) { Copy-Item .env.example .env }
   ```
   *Note: Default `.env` values work out-of-the-box for local SQLite and direct HTTP services.*

4. **Run Full Setup:**
   ```cmd
   .\setup.bat
   ```
   This will:
   - Check Python 3.11 and Node.js.
   - Build `.venv` (Image service, Gateway, Scan Management).
   - Build `.venv-scam` (Scam service and DistilBERT Hybrid engine).
   - Extract and verify scam model artifacts.
   - Build `.venv-phishing` (Phishing service and Regional Recall v1 ensemble).
   - Extract and verify phishing model artifacts.
   - Install frontend dependencies via `npm ci`.
   - Run model integrity verification.

---

### Scenario B: Modular Phishing Setup
*(For teammates who already set up Image and Scam, but missed Phishing)*

If your teammate has Image and Scam working and says: *"My scam and image work, but phishing folder / service is missing or not set up"*:

1. Ensure `TrustNet-Phishing-regional-recall-v1.zip` is placed in `exports/` (or that the 8 checkpoint files are in `models/phishing_url/checkpoints/regional_recall_v1/`).
2. Run the dedicated phishing setup command:
   ```cmd
   .\setup-phishing.bat
   ```
   *(Alternatively: `.\setup.bat phishing` or `.\setup.bat --phishing`)*

**What this does safely:**
- Creates `.venv-phishing` without touching `.venv` or `.venv-scam`.
- Installs `services/phishing_url/requirements-runtime.txt`.
- Extracts and checks all 8 component checksums against `manifest.json`.
- Outputs `PASS: regional-recall-v1 manifest and all eight component SHA-256 checksums match.`

---

### Scenario C: Modular Scam Setup
*(For teammates who need only the Scam Message environment)*

1. Ensure `TrustNet-Scam-Model-message-distilbert-lexical-links-hybrid-4.zip` is placed in `exports/`.
2. Run:
   ```cmd
   .\setup-scam.bat
   ```
   *(Alternatively: `.\setup.bat scam` or `.\setup.bat --scam`)*

---

## 4. How to Properly Examine and Test the Project

After setup, verify everything with these verification commands:

### 1. Verify Both Models in One Command
```cmd
.\setup.bat --verify
```
Expected output:
```text
[VERIFICATION] Verifying scam model...
{"integrity": "PASS", "model_version": "message-distilbert-lexical-links-hybrid-4", ...}
[VERIFICATION] Verifying phishing model...
PASS: regional-recall-v1 manifest and all eight component SHA-256 checksums match.
[PASS] All models and checksums verified successfully.
```

### 2. Examine Phishing URL Service & Model
```powershell
# Verify model files and SHA-256 checksums
.\.venv-phishing\Scripts\python.exe scripts/packaging/package-phishing-team.py --verify

# Run phishing automated test suite (114+ tests)
.\.venv-phishing\Scripts\python.exe -m pytest models/phishing_url/tests services/phishing_url/tests
```

### 3. Examine Scam Message Service & Link Fusion
```powershell
# Verify scam model integrity
.\.venv-scam\Scripts\python.exe scripts/checks/verify-scam.py

# Run scam message & link fusion test suite (including genuine offer letter & conference tests)
.\.venv-scam\Scripts\python.exe -m pytest services/scam_message/tests
```

### 4. Examine Scan Management & Shared Contracts
```powershell
.\.venv\Scripts\python.exe -m pytest services/scan_management/tests shared/tests
```

### 5. Examine TrustNet Mail Chrome Extension
```powershell
node --test extensions/trustnet-mail/tests/worker.test.cjs
```

---

## 5. Starting and Running the Full Application

1. **Launch all services:**
   ```cmd
   .\start-dev.bat
   ```
   This starts the background services:
   - **Frontend:** http://localhost:5173
   - **API Gateway:** http://localhost:8000
   - **Auth Service:** http://localhost:8001
   - **Scam Message Service:** http://localhost:8002
   - **Image Forensics Service:** http://localhost:8003
   - **Scan Management Service:** http://localhost:8004
   - **Trust Engine:** http://localhost:8005
   - **Phishing URL Service:** http://localhost:8007

2. **Open the Web Application:**
   Navigate to **http://localhost:5173** in your browser and register/login with your credentials.

3. **Stop all services when done:**
   ```cmd
   .\stop-dev.bat
   ```

---

## 6. Setting up the Chrome / Edge Extension (TrustNet Mail)

1. Open your browser and navigate to:
   - Chrome: `chrome://extensions`
   - Edge: `edge://extensions`
2. Turn ON **Developer mode** (top-right corner).
3. Click **Load unpacked** (top-left).
4. Select the directory:
   `<REPO_PATH>\extensions\trustnet-mail`
5. Open Gmail (`https://mail.google.com/`).
6. Click the TrustNet extension icon in your toolbar, log in or connect your dashboard session, and open any email to see the real-time TrustNet analysis card.
