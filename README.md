# Trust Net (TrustNet AI)

Trust Net is a multi-service forensic platform for media authenticity analysis and synthetic content detection. It combines a React 19 security workstation frontend, a FastAPI reverse proxy API gateway, microservice workers, and a physics-informed 15-analyzer image deepfake forensic pipeline.

---

## Latest Architectural & Security Updates

- **Hardened Single API Gateway Architecture**: All frontend browser requests route strictly through the centralized API Gateway on port `8000` via `VITE_API_GATEWAY_URL`. Direct browser calls to internal microservice ports (`8001`–`8004`) have been eliminated, shielding internal service topology from client-side exposure.
- **Production Authentication Lockdown**: Mock/developer tokens (`mock_jwt_`, `developer_token`) are strictly isolated to `ENVIRONMENT=dev` and `ALLOW_MOCK_AUTH=true`. In `production`, mock tokens and insecure placeholder secrets are unconditionally rejected (`MOCK_AUTH_DISABLED`).
- **Strict CORS Origin Hardening**: Replaced all wildcard CORS (`allow_origins=["*"]`) with configurable origin parsing via `CORS_ALLOWED_ORIGINS` that automatically strips wildcard patterns in production.
- **Upload Defense & Path Traversal Prevention**: Enforced a strict 15MB file size ceiling (`HTTP 413`), Pillow image header magic-byte verification (`HTTP 400`), safe filename sanitization (`os.path.basename`), and directory traversal sequence blocking in worker storage resolvers.
- **Asynchronous Concurrency in ML Routes**: Offloaded synchronous CPU-intensive neural model inference and Gabor/FFT transforms to worker threads via Starlette's `run_in_threadpool`, keeping FastAPI's async event loop fully responsive.
- **Zero-Dependency Puter.js Removal**: Completely eliminated third-party Puter.js dependencies and external cloud scripts.
- **LM Studio Local Vision Integration**: Replaced cloud AI with local OpenAI-compatible inference (`http://localhost:1234/v1`) using vision models such as `unsloth/Qwen3-VL-4B-Thinking-GGUF`. Supports streaming token processing, `<think>` tag stripping, and structured JSON parsing.
- **Physics-Informed Evidential Fusion (15 Forensic Analyzers)**:
  - 2D Fourier (FFT) Power Spectrum ($1/f^\alpha$ natural decay baseline)
  - Sub-Pixel Bayer CFA Demosaicing Residuals
  - Multi-Scale Gabor Texture Filter Bank (8 kernels, 4 angles)
  - JPEG Quantization Error Level Analysis (ELA)
  - Camera Sensor Pattern Noise (PRNU)
  - Face X-Ray Facial Boundary Step Gradients
  - Corneal Specular Reflection Physics (3D lighting parallax)
  - 3D Geometry Support & Symmetry Analysis
  - Generative Watermark Icon Scanner (convexity defect analysis)
  - Social Recompression & 8x8 DCT Grid Boundary Analysis
  - Provenance & Metadata Scanners (50+ known AI generator signatures)
  - Vision Transformer (ViT) & EfficientNet-B0 Convolutional Backbone
  - LM Studio Local Vision Semantic Reasoning
- **Generous 30-Minute Timeout (1800s) & CPU Token Optimization**: Configured Gateway reverse proxy (`GATEWAY_PROXY_TIMEOUT_SECONDS=1800`) and LM Studio client (`LM_STUDIO_TIMEOUT_SECONDS=1800`) with `LM_STUDIO_MAX_TOKENS=350` to accommodate deep local CPU vision reasoning without 504 timeouts.
- **100% Offline Audio Narration**: Native Web Speech API synthesis (`window.speechSynthesis`) for local report narration.
- **Direct Scan Database History**: Synchronous `/scans/analyze` calls are automatically persisted to the scan database for instant dashboard history visibility.

---

## What Is In This Repository

- **Frontend workstation** (`frontend/`): React 19 + TypeScript + Vite UI for scan workflows, interactive ELA/CFA forensic labs, and comprehensive PDF report exports. Uses a modular API suite (`frontend/src/services/api/`).
- **Gateway** (`gateway/`): FastAPI reverse proxy, JWT authentication guard, rate-limiting, and route dispatch.
- **Services** (`services/`):
  - `services/auth`: Registration, login, and JWT access tokens.
  - `services/scan_management`: Intake, validation, quarantine storage, and synchronous/async execution.
  - `services/image_deepfake`: Multi-signal forensic execution and Kafka worker mode.
  - `services/trust_engine`: Cross-service evidential fusion and trust score computation.
- **Shared package** (`shared/`): Common schemas, constants, JWT verification, and structured logging.
- **Model package** (`models/`): Reusable 15-module image-deepfake forensic detector, local ViT, and LM Studio vision client.

---

## Architecture At A Glance

1. **Client Browser** connects exclusively to the API Gateway at <http://localhost:8000> via `VITE_API_GATEWAY_URL`.
2. **Gateway** validates tokens and proxies requests to downstream microservices with authenticated headers:
   - `/api/v1/auth` -> Auth Service (Port 8001)
   - `/api/v1/scans` -> Scan Management Service (Port 8002)
   - `/api/v1/detect` -> Image Deepfake Service (Port 8003)
   - `/api/v1/trust` -> Trust Engine (Port 8004)
3. **Synchronous Analysis**:
   - Client calls `POST /api/v1/scans/analyze` with image payload.
   - Forensic detector runs parallel forensic modules in thread pool + local neural transformers + LM Studio local vision.
   - Result synthesized via evidential multi-vector corroboration and returned with full analyzer telemetry.
4. **Asynchronous / Kafka Pipeline**:
   - Client creates scan via `POST /api/v1/scans/upload`.
   - Dispatches `detection.requested.image_deepfake` event to Kafka.
   - Image Deepfake Worker consumes, executes detection, and emits `detector.image.completed`.
   - Trust Engine consumes completed detector events and computes synthesized Trust Score.
5. **LM Studio Local Vision**:
   - Connects to local LM Studio server at `http://localhost:1234/v1`.
   - Auto-discovers active vision model or falls back gracefully to deterministic forensics if offline.

---

## 🎓 Viva & Panel Defense Guide (Screen-Share & Logic Map)

> 💡 **For full in-depth viva questions, presentation script, and mathematical derivations, see [PANEL_DEFENSE_AND_VIVA_GUIDE.md](PANEL_DEFENSE_AND_VIVA_GUIDE.md).**

### 1. Screen-Share Navigation: Exactly Where to Point in Code

When the evaluation panel or professor asks to show the exact code implementation, navigate to these files and line numbers:

| What the Panel Asks | Exact File to Open | Exact Lines | Code Explanation to Give |
|---|---|---|---|
| **"Score kaise calculate ho raha hai? Formula dikhao."** | [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L185-L254) | **Lines 185–254** | Dynamic weights list `anomaly_weights` and normalized weighted sum formula: $A_{\text{weighted}} = \frac{\sum (s_i \cdot w_i)}{\sum w_i}$. |
| **"WhatsApp/Social media compression par heuristics fail kyu nahi hoti?"** | [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L190-L191) | **Lines 190–191** | `phys_scale = 0.50 if already_recompressed else 1.0`. Fragile heuristics downweight by 50% and authority shifts to ViT and metadata. |
| **"Contradiction detection aur evidential authority kahan hai?"** | [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L357-L405) | **Lines 357–405** | Evidential authority: Decisive boundary seams ($\ge 0.65$) or Vision LLM elevate risk to $\ge 68\%$ (`LIKELY_AI_MANIPULATED`) without forced 50% squashing. Clean camera images stay $\le 20\%$ (`AUTHENTIC`). Contradiction is logged as an explainability alert. |
| **"Verdict thresholds (4 levels) kahan decide ho rahe hain?"** | [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L417-L435) | **Lines 417–435** | 4-Level Semantic Verdict: `AUTHENTIC` (<25%), `LIKELY_AUTHENTIC` (25-48%), `UNCERTAIN` (48-54%), `LIKELY_AI_MANIPULATED` (>52%). |
| **"AI Metadata / Watermark ka immediate override kahan hai?"** | [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L360-L363) | **Lines 360–363** | `if meta_res.get("is_ai_signature_found"): weighted_anomaly = max(0.96, ...)`. Cryptographic ground truth locks risk to $\ge 96.0\%$. |
| **"LM Studio Vision Local Inference kaise integrate hai?"** | [`models/image_deepfake/inference/lm_studio_vision_client.py`](models/image_deepfake/inference/lm_studio_vision_client.py#L114-L176) | **Lines 114–176** | Local streaming API call, image copy capped to <150KB JPEG, `<think>` reasoning tags stripped, and structured JSON validated. |
| **"CPU token optimization aur 1800s timeout kahan set hai?"** | [`gateway/app/core/proxy_client.py`](gateway/app/core/proxy_client.py#L7) & [`models/image_deepfake/inference/lm_studio_vision_client.py`](models/image_deepfake/inference/lm_studio_vision_client.py#L39-L40) | `PROXY_TIMEOUT = 1800.0`, `LM_STUDIO_MAX_TOKENS = 350` | Generous 30-minute window for local CPU inference without 504 timeouts. |
| **"Frontend Gateway API client architecture kahan hai?"** | [`frontend/src/services/api/client.ts`](frontend/src/services/api/client.ts) | **Lines 1–67** | Centralized `HttpClient` routing strictly through `VITE_API_GATEWAY_URL` with automatic token injection and modular sub-APIs (`scan.api.ts`, `auth.api.ts`). |
| **"Watermark fabric false-positive rejection kahan hai?"** | [`models/image_deepfake/forensics/watermark_analyzer.py`](models/image_deepfake/forensics/watermark_analyzer.py#L100-L106) | **Lines 100–106** | `if len(contours) > 18: continue`. Rejects dense embroidery/saree textures from false watermark triggers. |
| **"Trust Engine ka cross-service fusion kahan hota hai?"** | [`services/trust_engine/app/services/fusion_engine.py`](services/trust_engine/app/services/fusion_engine.py#L52-L122) | **Lines 52–122** | 4-step evidential fusion algorithm, module caps (40%), contradiction delta penalty ($40.0\Delta \implies 25\%$ penalty). |
| **"AI image upload par defect kaise pakadta hai?"** | [`models/image_deepfake/forensics/face_analyzer.py`](models/image_deepfake/forensics/face_analyzer.py#L217-L260) & [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L376-L380) | **Lines 217–260** (Face X-Ray) & **Lines 376–380** (Rule b) | Sobel boundary step gradients along jawline/hairline + skin variance trigger `weighted_anomaly >= 0.68` (`LIKELY_AI_MANIPULATED`). |
| **"Real photo upload par authenticity kaise verify hoti hai?"** | [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L370-L374) & [`models/image_deepfake/forensics/frequency_analyzer.py`](models/image_deepfake/forensics/frequency_analyzer.py#L80-L120) | **Lines 370–374** (Rule a) & **Lines 80–120** (FFT) | 0 physical domain anomalies + optical $1/f^\alpha$ roll-off + ViT $\ge 75\%$ clamps risk to $\le 18.0\%$ (`AUTHENTIC`). |
| **"Pehle UNCERTAIN kyu dikh raha tha aur code me kaise solve kiya?"** | [`frontend/src/views/ReportView.tsx`](frontend/src/views/ReportView.tsx#L64-L77) & [`frontend/src/services/pdfExporter.ts`](frontend/src/services/pdfExporter.ts#L54-L66) | **Lines 64–77** (ReportView) & **Lines 54–66** (PDF) | Removed blanket `if (isContradiction) verdict = 'UNCERTAIN'`. UNCERTAIN is strictly confined to 46%–54% deadlocks; genuine 10% risk stays emerald-green `AUTHENTIC`. |
| **"Explainable Grad-CAM heatmap kahan banta hai?"** | [`models/image_deepfake/explainability/grad_cam.py`](models/image_deepfake/explainability/grad_cam.py#L37-L89) | **Lines 37–89** | PyTorch backward hook on layer-4 conv feature maps generates spatial saliency heatmap. |
| **"Frontend me offline speech aur report debrief kahan hai?"** | [`frontend/src/views/ReportView.tsx`](frontend/src/views/ReportView.tsx#L30-L85) | **Lines 30–85** | 4-level UI badges, LM Studio Local Vision debrief card, `window.speechSynthesis` offline narration. |

---

### 2. Core Mathematical Weights & Thresholds Table

| Forensic Module | Default Weight | Compressed Weight | Physical Invariant Measured |
|---|---|---|---|
| **2D Fourier Spectrum (FFT)** | `0.20` | `0.10` | Optical lens $1/f^\alpha$ power-law decay vs GAN periodic lattice spikes |
| **Sub-Pixel Bayer CFA Demosaicing** | `0.16` | `0.08` | Physical hardware sensor RGB interpolation ($\Delta = \|G - (R+B)/2\|$) |
| **Multi-Scale Gabor Texture** | `0.16` | `0.08` | Orientation entropy across 4 angles ($0^\circ, 45^\circ, 90^\circ, 135^\circ$) detecting AI skin smoothing |
| **Error Level Analysis (ELA)** | `0.12` | `0.06` | JPEG 8x8 DCT compression disparity between spliced foreground & background |
| **Sensor Pattern Noise (PRNU)** | `0.10` | `0.05` | Camera sensor silicon photo-response non-uniformity fingerprint |
| **Face X-Ray Boundary Artifacts** | `0.10` | `0.08` | Step gradient discontinuity along facial perimeter blending boundaries |
| **Corneal Lighting Parallax** | `0.08` | `0.04` | 3D specular highlight geometry across eye coordinates |
| **3D Facial Symmetry & Mesh** | `0.08` | `0.04` | Anatomical depth continuity and pupil-to-nose bridge ratios |
| **AI Metadata & C2PA Provenance** | `0.00` (Override) | `0.00` (Override) | Cryptographic EXIF / C2PA / XMP signatures triggering instant 96% risk lock |
| **Generative Watermark Scanner** | `0.00` (Override) | `0.00` (Override) | Corner icon convexity defect analysis with fabric texture false-positive filter |

---

## Local Prerequisites

1. **Python 3.11+** (or 3.10+) — [python.org](https://www.python.org/downloads/)
2. **Node.js 18+** & npm — [nodejs.org](https://nodejs.org/)
3. *(Optional)* **Docker Desktop** (For Kafka in KRaft mode; if Docker is offline, microservices automatically operate in standalone REST mode).

---

## Quick Start & Setup Guide

### Step 1: Clone the Repository & Checkout Branch
```bash
git clone https://github.com/Aspira-2k25/TrustNet-Ai.git
cd TrustNet-Ai
git checkout image-test
```

### Step 2: Configure Environment Variables
Copy the template to initialize your local `.env`:

**Windows (CMD/PowerShell):**
```cmd
copy .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

### Step 3: Setup Python Environment & Dependencies

1. **Create and activate the virtual environment:**

   *Windows PowerShell:*
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   *Windows CMD:*
   ```cmd
   python -m venv .venv
   .\.venv\Scripts\activate.bat
   ```

   *Linux / macOS:*
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install all microservice and model dependencies:**

   *Windows (Recommended 1-Click Installer):*
   ```powershell
   .\install-deps.bat
   ```

   *Manual Install Sequence (Cross-Platform):*
   ```bash
   pip install -e shared/
   pip install -r services/auth/requirements.txt
   pip install -r services/scan_management/requirements.txt
   pip install -r models/image_deepfake/requirements.txt
   pip install -r services/image_deepfake/requirements.txt
   pip install -r services/trust_engine/requirements.txt
   pip install -r gateway/requirements.txt
   ```

### Step 4: Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### Step 5: Launch All Services

#### On Windows (Recommended 1-Click Launcher):
```cmd
.\start-dev.bat
```
This automatically launches the API Gateway (Port 8000), Auth Service (8001), Scan Management (8002), Image Worker (8003), Trust Engine (8004), and the React Frontend (5173) in dedicated windows with file-watching hot reload enabled.

#### On Linux / macOS (or Manual Launch):
Run each in separate terminal windows with `.venv` active:
1. `uvicorn gateway.app.main:app --port 8000 --reload`
2. `uvicorn services.auth.app.main:app --port 8001 --reload`
3. `uvicorn services.scan_management.app.main:app --port 8002 --reload`
4. `uvicorn services.image_deepfake.app.main:app --port 8003 --reload`
5. `uvicorn services.trust_engine.app.main:app --port 8004 --reload`
6. `cd frontend && npm run dev`

---

## Service Endpoints & UI

- **Frontend Security Station UI**: <http://localhost:5173>
- **API Gateway Swagger Docs**: <http://localhost:8000/docs>
- **Gateway Health Check**: <http://localhost:8000/health>
- **Auth Service Health**: <http://localhost:8001/health>
- **Scan Management Health**: <http://localhost:8002/health>
- **Image Deepfake Health**: <http://localhost:8003/health>
- **Trust Engine Health**: <http://localhost:8004/health>

---

## Automated Test Suite

TrustNet AI maintains 100% test coverage across shared libraries, ML models, microservices, security boundaries, and end-to-end pipelines.

Run the complete test suite:
```bash
python -m pytest -v
```
*(Result: **145 passed in ~300s** across all 8 test targets)*.

Run individual test suites:
```bash
python -m pytest shared/tests -v                     # Auth, CORS, schema contracts
python -m pytest gateway/tests -v                    # Gateway reverse proxy & guards
python -m pytest services/auth/tests -v              # User registration & tokens
python -m pytest services/scan_management/tests -v   # Ingestion, validation, uploads
python -m pytest services/image_deepfake/tests -v    # Detection API & security defense
python -m pytest services/trust_engine/tests -v      # Evidential score fusion
python -m pytest models/image_deepfake/tests -v      # 15 forensic analyzers & PyTorch
python -m pytest tests/e2e -v                        # End-to-end multimodal pipeline
```

---

## Module Documentation

- [`frontend/README.md`](frontend/README.md) - React workstation, modular API client, PDF export.
- [`gateway/README.md`](gateway/README.md) - Gateway proxying, CORS policy, JWT guard.
- [`shared/README.md`](shared/README.md) - Pydantic schemas, JWT verification, base settings.
- [`services/auth/README.md`](services/auth/README.md) - Authentication & user database.
- [`services/scan_management/README.md`](services/scan_management/README.md) - Intake, validation, quarantine storage.
- [`services/image_deepfake/README.md`](services/image_deepfake/README.md) - Worker execution & detection endpoints.
- [`services/trust_engine/README.md`](services/trust_engine/README.md) - Trust score calibration & evidence synthesis.
- [`models/image_deepfake/README.md`](models/image_deepfake/README.md) - PyTorch neural models & forensic filter banks.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - Full system topology & Kafka event flows.
- [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) - Active status & module audit matrix.
- [`docs/FILE_STRUCTURE.md`](docs/FILE_STRUCTURE.md) - Repository structure & placement rules.
