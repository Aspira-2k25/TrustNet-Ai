# Trust Net (TrustNet AI)

Trust Net is a multi-service forensic platform for media authenticity analysis. It combines a React frontend, a FastAPI gateway, microservices, and a multi-signal image deepfake pipeline.

## Latest Updates

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
- **Generous 30-Minute Timeout (1800s) & CPU Token Optimization**: Configured Gateway reverse proxy (`GATEWAY_PROXY_TIMEOUT_SECONDS=1800`) and LM Studio client (`LM_STUDIO_TIMEOUT_SECONDS=1800`) with `LM_STUDIO_MAX_TOKENS=350` to accommodate deep local CPU vision reasoning without 504 timeouts or connection drops.
- **Resilient 3-Tier Microservice Fallback**: Frontend automatically fails over from Gateway (Port 8000) directly to Scan Management (Port 8002) and standalone Deepfake Detector (Port 8003), ensuring zero client-side aborted scans even during heavy local computation.
- **Universal Gateway Proxying**: Added routes for Auth (8001), Scan Management (8002), Image Deepfake (8003), and Trust Engine (8004).
- **100% Offline Audio Narration**: Native Web Speech API synthesis (`window.speechSynthesis`) for local report narration.
- **Direct Scan Database History**: Synchronous `/scans/analyze` calls are automatically persisted to the scan database for instant dashboard history visibility.

## What Is In This Repository

- **Frontend workstation**: React + Vite UI for scan workflows, interactive ELA/CFA forensic labs, and comprehensive PDF report exports.
- **Gateway**: FastAPI reverse proxy, rate-limiting, and route dispatch.
- **Services**:
  - `services/auth`: Registration, login, and JWT access tokens.
  - `services/scan_management`: Intake, validation, storage, and synchronous/async execution.
  - `services/image_deepfake`: Multi-signal forensic execution and Kafka worker mode.
  - `services/trust_engine`: Cross-service evidential fusion and trust score computation.
- **Shared package**: Common schemas, constants, JWT verification, and structured logging.
- **Model package**: Reusable 15-module image-deepfake forensic detector, local ViT, and LM Studio vision client.

## Architecture At A Glance

1. **Client** connects to API Gateway at <http://localhost:8000>.
2. **Gateway** routes requests to downstream microservices:
   - `/api/v1/auth` -> Auth Service (Port 8001)
   - `/api/v1/scans` -> Scan Management Service (Port 8002)
   - `/api/v1/detect` -> Image Deepfake Service (Port 8003)
   - `/api/v1/trust` -> Trust Engine (Port 8004)
3. **Synchronous Analysis**:
   - Client calls `POST /api/v1/scans/analyze` with image payload.
   - Forensic detector runs 10 parallel forensic modules in thread pool + local neural transformers + LM Studio local vision.
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
| **"Frontend microservice direct fallback kahan hai?"** | [`frontend/src/services/api.ts`](frontend/src/services/api.ts#L120-L145) | **Lines 120–145** | Resilient 3-tier fallback (Port 8000 Gateway -> Port 8002 Scan Service -> Port 8003 Detector) preventing aborted scans. |
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
| **Face X-Ray Boundary Seams** | `0.25` | `0.25` | Step gradients along facial blending boundaries (jawline, orbital perimeter) |
| **Corneal Specular Reflection** | `0.20` | `0.20` | 3D environmental lighting parallax vectors reflected across both pupils |
| **3D Geometry & Perspective** | `0.18` | `0.18` | Hough line transform checking vanishing lines and structural building symmetry |
| **Vision Transformer (ViT)** | `0.30` | `0.42` | Global patch-level self-attention deep learning model trained on 140,000 crops |
| **LM Studio Local Vision** | `0.18` | `0.18` | Visual semantic reasoning (anatomy coherence, lighting, edge realism) |
| **Watermark Icon Scanner** | `0.15` | `0.15` | Convexity defect pointedness check with fabric density filter (`contours <= 18`) |
| **Semantic Scene Context** | `0.12` | `0.22` | Dynamic domain weight adjustment (Anime, Digital Art, Screenshot, Nature, Portrait) |

---

### 3. Top 5 Viva Questions & Instant Answers

#### Q1: "Why did you combine physics forensics with Deep Learning instead of using just CNN/ViT?"
> **Answer:** *"Pure deep learning models suffer from high false-positive rates on real photos and break under compression because they are black boxes. TrustNet couples learned representations with 12 deterministic mathematical invariants derived from optical physics (lens diffraction, Bayer CFA demosaicing, and corneal reflection parallax). This ensures that an image is flagged only when multiple independent physical domains corroborate the manipulation."*

#### Q2: "What is Evidential Authority and how does it handle conflicting signals?"
> **Answer:** *"Instead of artificially squashing conflicting detections into a 50% UNCERTAIN band, TrustNet respects decisive physical evidence: if Face X-Ray boundary discontinuity is detected ($\ge 0.65$) or the Local Vision LLM identifies generative skin textures, risk properly elevates to $\ge 68\%$ (`LIKELY_AI_MANIPULATED`). Real camera photos with intact sensor noise remain $\le 20\%$ (`AUTHENTIC`). Contradiction is logged as an explainability alert to maintain full scientific transparency."*

#### Q3: "What is the role of LM Studio Local Vision and why did you remove Puter.js?"
> **Answer:** *"Puter.js was a third-party cloud script that leaked user media to external servers and required an active internet connection. We replaced it with a local-first OpenAI-compatible vision client running `unsloth/Qwen3-VL-4B-Thinking-GGUF` at `http://localhost:1234/v1`. It acts as a visual reasoning assistant — analyzing fine textures, anatomy boundaries, and lighting anomalies — with zero cloud cost, 100% data privacy, and graceful offline fallback."*

#### Q4: "How does the system handle images from WhatsApp or Instagram?"
> **Answer:** *"Social platforms apply lossy 8x8 DCT re-compression. Our `RecompressionAnalyzer` measures cross-pixel DCT grid boundaries to calculate the Blockiness Ratio. If re-compression is detected, it scales down fragile physical heuristics by 50% (`phys_scale = 0.50`) and shifts authority to the robust ViT classifier, metadata provenance, and watermark detection."*

#### Q5: "How does Grad-CAM provide explainability?"
> **Answer:** *"Grad-CAM computes partial derivatives of the predicted class score with respect to convolutional layer-4 feature maps in EfficientNet-B0. It generates a 2D spatial saliency heatmap that visually highlights the exact image regions (e.g. periocular boundary, jawline blending seams) that contributed to the verdict."*

---

## 🏛️ Comprehensive Architecture & Algorithms Catalog (Full Platform)

TrustNet AI is designed as a unified multimodal trust and security intelligence platform covering 4 key threat vectors:

```
+---------------------------------------------------------------------------------------------------------+
|                                        TrustNet AI Architecture                                         |
+---------------------------------------------------------------------------------------------------------+
| [User] --> [Frontend (React 19)] --> [API Gateway (8000)] --> [Backend Services] --> [Event Bus (Kafka)] |
+---------------------------------------------------------------------------------------------------------+
|  [1. Phishing Detection]   | [2. Scam Message]    | [3. Fake Review]     | [4. Multimodal Deepfake]     |
|  - URL, Domain, SSL        | - Text, Keywords     | - Semantic Sim.      |  * Image: ELA, PRNU, ViT     |
|  - WHOIS, HTML, JS         | - Urgency, Semantic  | - Behaviour, Sentim. |  * Audio: MFCC, Wav2Vec2     |
|  - LightGBM, RF, XGB, BERT | - RoBERTa, DistilBERT| - SBERT, Isol.Forest |  * Video: LipSync, rPPG, EAR |
+---------------------------------------------------------------------------------------------------------+
|                                    [Trust Score Engine (Port 8004)]                                     |
|                   Weighted Fusion + Contradiction Detection + Explainable AI (0-100)                     |
+---------------------------------------------------------------------------------------------------------+
```

### Module 1: Phishing Detection (Web & URL Threat Intelligence)
- **Features & Signals:**
  - **Lexical Analysis:** URL length, Shannon entropy, subdomain depth, and Levenshtein edit distance against top Alexa 10k legitimate domains to detect typosquatting (e.g. `goog1e.com`).
  - **Domain & SSL Invariants:** WHOIS registration age (domains $< 48$ hours old have high malicious propensity), certificate authority verification, and SSL expiry.
  - **HTML/JS DOM Parsing:** Hidden `<iframe>` tags, external `<form action>` target URLs, password input fields without HTTPS, and obfuscated JavaScript execution patterns.
- **Algorithms & ML Models:**
  - **LightGBM / XGBoost / Random Forest:** Gradient boosted tree ensemble trained on 80+ tabular lexical and network features for sub-5ms classification.
  - **BERT:** Transformer language model to encode URL paths and HTML title tags for contextual social engineering intent.
- **Output:** Phishing Risk Score ($0.0 - 100.0\%$).

### Module 2: Scam Message Detection (SMS, WhatsApp, Email NLP)
- **Features & Signals:**
  - **Keyword & Trigger Patterns:** Regex and TF-IDF extraction of financial pressure words ("Lottery", "KYC blocked", "UPI pin", "Account suspended").
  - **Psychological Urgency Metric:** NLP heuristic that quantifies artificial panic phrases ("act within 1 hour", "legal penalty").
  - **Semantic Intent Classification:** Identifies whether the message coerces the recipient into an external action (clicking link, sending money).
- **Algorithms & ML Models:**
  - **DistilBERT / RoBERTa:** Fine-tuned sequence classification transformers that analyze context rather than naive keyword matching, capturing evasive spelling and obfuscated scam phrasing.
- **Output:** Scam Probability Score ($0.0 - 100.0\%$).

### Module 3: Fake Review Detection (E-Commerce & App Store Fraud)
- **Features & Signals:**
  - **Semantic Duplication (Astroturfing Rings):** Sentence-BERT (SBERT) generates 768-dimensional dense vectors for reviews. If multiple accounts post reviews with Cosine Similarity $> 0.90$, they are grouped into an automated review syndicate.
  - **Behavioral & Temporal Burstiness:** Measures unnatural velocity (e.g., 50 reviews in 30 minutes on a low-traffic product), reviewer account age, and review distribution variance.
  - **Sentiment-Rating Disparity:** Natural language sentiment vs numerical star rating contradiction (e.g., negative text with a 5-star rating).
- **Algorithms & ML Models:**
  - **Isolation Forest:** Unsupervised anomaly detection algorithm that isolates irregular review bursts with few tree partitions.
  - **XGBoost:** Supervised classifier trained on reviewer tenure, verified purchase tags, and sentiment alignment.
- **Output:** Authenticity Score ($0.0 - 100.0\%$).

### Module 4: Multimodal Deepfake Detection (Image · Audio · Video)

#### 4.1 Image Deepfake Detection (✅ Active & Production-Ready in Repo)
- **Physics Forensics:**
  - **2D Fourier Spectrum (FFT):** Radial power-law decay ($1/f^\alpha$) vs periodic GAN/diffusion lattice spikes.
  - **Bayer CFA Demosaicing:** Hardware sensor demosaicing continuity ($\Delta = \|G - (R+B)/2\|$).
  - **Multi-Scale Gabor Filter:** Texture orientation entropy across 4 angles ($0^\circ, 45^\circ, 90^\circ, 135^\circ$).
  - **Error Level Analysis (ELA):** JPEG 8x8 DCT re-compression variance between spliced foreground and background.
  - **Sensor Pattern Noise (PRNU):** Silicon photo-response non-uniformity fingerprint extraction.
  - **Face X-Ray:** Boundary seam step gradients along facial perimeter.
  - **Corneal Specular Reflection:** 3D lighting vector parallax across both pupils.
  - **Watermark Scanner with Fabric Rejection:** Corner glyph pointedness check with contour density thresholding (`len(contours) > 18` rejects fabric/saree embroidery).
- **Deep Learning & Visual Reasoning:**
  - **EfficientNet-B0 Backbone:** Convolutional spatial feature extractor.
  - **Local Vision Transformer (ViT):** Patch self-attention trained on 140k FaceForensics++ crops with offline fallback.
  - **LM Studio Local Vision Reasoning:** `Qwen3-VL-4B-Thinking` running locally on `http://localhost:1234/v1` with `<think>` tag stripping and prompt-guided diffusion artifact evaluation.
  - **Grad-CAM Explainability:** Saliency heatmaps highlighting exact suspicious facial regions.
- **Output:** Image Deepfake Score ($0.0 - 100.0\%$).

#### 4.2 Audio Deepfake Detection (Planned Roadmap)
- **MFCC (Mel-Frequency Cepstral Coefficients) & FFT Formants:** Biological vocal tract acoustic resonance analysis vs synthetic phase discontinuities.
- **Breathing & Biological Pause Analysis:** Real humans exhibit diaphragmatic breathing and natural acoustic pauses; synthetic voice engines exhibit mathematical silence ($-\infty$ dB).
- **Wav2Vec2 Self-Supervised Transformer:** Encodes raw 16kHz audio waveforms into latent speech representations to detect synthetic voice clones.
- **Vocoder Detection:** Identifies periodic transposed-convolution phase artifacts left by HiFi-GAN and MelGAN vocoders.
- **Output:** Audio Deepfake Score ($0.0 - 100.0\%$).

#### 4.3 Video Deepfake Detection (Phase 2 Roadmap)
- **Optical Flow (Farneback / Lucas-Kanade):** Evaluates frame-to-frame motion vectors to detect temporal jitter and boundary shimmering during head turns.
- **Lip-Sync Audio-Visual Alignment (SyncNet / Wav2Lip):** Calculates cross-modal distance between spoken phonemes and visual mouth visemes.
- **rPPG (Remote Photoplethysmography):** Extracts facial skin Green-channel micro-color oscillations corresponding to cardiac blood volume pulse (BVP). Synthetic AI faces lack genuine human heartbeat waveforms.
- **Blink Dynamics (Eye Aspect Ratio - EAR):** Measures physiological eyelid closure curves ($EAR = \frac{\|p_2-p_6\| + \|p_3-p_5\|}{2\|p_1-p_4\|}$) to detect abnormal or absent blinks.
- **Output:** Video Deepfake Score ($0.0 - 100.0\%$).

### Module 5: Trust Score Engine (Port 8004 — Central Fusion Brain)
- **Multi-Vector Evidential Fusion:** Combines scores from all active threat modules into a single, calibrated Trust Score ($0 - 100$).
- **Contradiction Resolution:** Applies a 25% confidence penalty if any two detectors strongly disagree ($\Delta \ge 40.0$).
- **Module Weight Caps:** Imposes a 40% cap on any single detector's influence to prevent single-point-of-failure vulnerabilities.
- **Natural Language Debrief:** Generates human-readable forensic audit trails explaining the exact physical and statistical evidence.

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
