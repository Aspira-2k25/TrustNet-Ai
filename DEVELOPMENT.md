# TrustNet AI — Developer, Researcher & Agent Handoff Guide

**Baseline Release Version**: `v1.0.0-frozen-baseline`  
**Automated Tests**: `91 / 91 Passing (100%)`  
**Baseline Status**: Strictly Frozen for Reproducibility  

---

## 1. Project Architecture

TrustNet implements two distinct architectural paths:

### A. Primary Interactive Workstation Path (Synchronous REST)
Used by the web analyst dashboard for sub-second interactive image forensic scans:
```
React 18 UI ──(POST /api/v1/scans/analyze)──► Gateway (8000) ──► Scan Management (8002) ──► EfficientNetDetector Engine ──► Response JSON ──► UI
```
*Latency*: $~150\text{ms}$ local execution + external HF API latency ($~800\text{ms}$, bounded by $3.5\text{s}$ timeout).

### B. Batch Ingestion Pipeline (Asynchronous Kafka 3.7 KRaft)
Used for headless queue-based bulk media ingestion:
```
Scan Upload ──► Kafka Topic: detection.requested.image_deepfake ──► Deepfake Worker (8003) ──► Kafka Topic: detection.completed.image_deepfake ──► Trust Engine (8004)
```

---

## 2. Quickstart & Local Execution

### Backend & Microservices
```powershell
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Run all microservices using unified dev script
.\start-dev.ps1
```
*Individual Service Ports*:
* **Gateway**: `http://localhost:8000`
* **Auth Service**: `http://localhost:8001`
* **Scan Management**: `http://localhost:8002`
* **Image Deepfake**: `http://localhost:8003`
* **Trust Engine**: `http://localhost:8004`

### Frontend Dashboard
```powershell
cd frontend
npm install
npm run dev
# Dashboard opens on http://localhost:5173
```

---

## 3. Running Automated Tests

```powershell
# Run the complete test suite (91 passing unit & integration tests)
.venv\Scripts\python -m pytest

# Run frontend type-check & production build
cd frontend
npm run build
```

---

## 4. How Image Analysis Works (Decision Pipeline)

When an image is submitted:
1. **Validation** (`models/image_deepfake/preprocessing/validator.py`): Checks MIME type, magic bytes (JPEG, PNG, WEBP, BMP, TIFF), and $10\text{MB}$ payload size limit.
2. **Scene Context Classification** (`models/image_deepfake/forensics/scene_analyzer.py`): Classifies media into semantic categories (e.g. Portrait, Landscape, Anime, Architecture) based on color saturation entropy and edge density.
3. **Face Localization** (`models/image_deepfake/forensics/face_analyzer.py`): Runs OpenCV Haar Cascades (`frontalface` + `profileface`).
4. **Conditional Domain Gating**:
   * *If face detected*: Activates **Face X-Ray Boundary Warping** and **Corneal Specular Reflection Parallax**; skips 3D Geometry.
   * *If no face detected*: Activates **3D Structural Geometry Support**; skips facial analyzers.
5. **Universal Forensic Analysis**: Executes 2D FFT Radial Spectrum, Error Level Analysis (ELA), Laplacian PRNU Noise Floor, Sub-Pixel Bayer CFA Demosaicing, and Provenance EXIF metadata matching.
6. **External Deepfake Model** (`models/image_deepfake/inference/huggingface_client.py`): Calls `dima806/deepfake_vs_real_image_detection` with $3.5\text{s}$ timeout fallback.
7. **Spatial Representation Extraction**: PyTorch `EfficientNet-B0` extracts 1280-dim spatial representations.
8. **Normalized Anomaly Fusion**: Calculates active weighted anomaly with multi-vector corroboration boost if $\ge 2$ independent signals trigger high anomaly.

---

## 5. Model Inventory & Real Roles

| Model / Subsystem | Implementation Category | Role in TrustNet | Contributes to Score? |
|---|---|---|---|
| **Hugging Face ViT** (`dima806/deepfake_vs_real_image_detection`) | **External Learned ML** | Primary learned deepfake classifier | **Yes (22.0% Active Weight)** |
| **EfficientNet-B0** | **Pre-trained CNN Backbone** | Extracts 1280-dim feature map representations & spatial variance | Feature extractor; classifier head pending fine-tuning |
| **2D FFT Spectrum** | **Digital Signal Processing** | High-frequency grid spikes ($>2.5\sigma$) & radial decay roll-off | **Yes (12.0% Active Weight)** |
| **Error Level Analysis (ELA)** | **Compression Forensics** | 8×8 DCT block recompression variance ($Q=90$) | **Yes (10.0% Active Weight)** |
| **Sensor Noise (PRNU)** | **Noise Floor Forensics** | High-pass Laplacian noise variance & kurtosis | **Yes (10.0% Active Weight)** |
| **Sub-Pixel Bayer CFA** | **Demosaicing DSP** | $2\times 2$ Color Filter Array lattice correlation & micro-jitter | **Yes (12.0% Active Weight)** |
| **OpenCV Face Detector** | **Computer Vision** | Frontal and profile facial bounding box localization | **Routing Gate** |
| **Face X-Ray Boundary Warping** | **Boundary Forensics** | Facial perimeter Sobel gradient & skin texture variance | **Yes (14.0% Active Weight when Face Present)** |
| **Corneal Reflection Parallax** | **Optics Physics** | Bilateral specular highlight symmetry across eyes | **Yes (10.0% Active Weight when Eyes Present)** |
| **3D Geometry Physics** | **Structural CV** | Bilateral ORB feature symmetry & ground contact lines | **Yes (10.0% Active Weight when Non-Face)** |
| **Provenance EXIF** | **Metadata Forensics** | Midjourney, Flux, SDXL, Fooocus software signature matching | **Yes (5.0% Active Weight)** |

---

## 6. Fusion Engine Mathematics

1. **Normalized Active Weighted Anomaly**:
   $$A_{\text{raw}} = \frac{\sum_{i \in \text{APPLIED}} s_i \cdot w_i}{\sum_{i \in \text{APPLIED}} w_i}$$
2. **Corroboration Rule**:
   $$\text{If } \text{count}(s_i \ge 0.70) \ge 2 \implies A = \max(0.72, \min(0.98, A_{\text{raw}} \times 1.15))$$
3. **Inversion & Risk Output**:
   $$P(\text{REAL}) = \text{clamp}(1.0 - A, 0.01, 0.99), \quad \text{RiskScore} = (1.0 - P(\text{REAL})) \times 100.0 \in [1.0, 99.0]$$
4. **Decision Thresholds**:
   * $\text{Risk} < 45.0 \implies \textbf{AUTHENTIC}$
   * $45.0 \le \text{Risk} < 75.0 \implies \textbf{SUSPICIOUS}$
   * $\text{Risk} \ge 75.0 \implies \textbf{AI\_GENERATED}$

---

## 7. Benchmarking & Dataset Evaluation

### Production vs. Benchmark Data Separation
* **Production Inference**: Requires **zero** local datasets. Operates purely on uploaded image streams.
* **Benchmarking & Validation**: Requires an **externally supplied** labelled dataset organized into `real/` and `fake/` directories. No dummy or demo images are stored in the repository.
* **EfficientNet Training**: EfficientNet training is currently **not** part of the production runtime. Production uses ImageNet-1K pretrained `EfficientNet-B0` solely as a spatial feature backbone.

### Running the Benchmark Suite on an External Dataset
```powershell
# Run formal scientific evaluation suite (10 standard metrics, data leakage audit, calibration, and ablation)
.venv\Scripts\python benchmark/benchmark_suite.py /path/to/external_dataset

# Run fast CLI evaluator
.venv\Scripts\python benchmark/evaluate.py --dataset-dir /path/to/external_dataset
```

**Benchmark Validity Note:** Benchmarking results are only scientifically valid when executed against verified, held-out real vs. fake datasets with Hugging Face ViT online. If Hugging Face is offline or rate-limited, the benchmark engine flags ViT-only ablation metrics as `INVALID` and evaluates the remaining forensic signals in degraded mode.

---

## 8. Current Limitations & Future Work

### Documented Limitations
1. **Extreme Profile Faces**: Profile angles $> 60^\circ$ and heavy ocular occlusions reduce Haar cascade recall.
2. **Heavy Social-Media Recompression**: Downsampling ($< 256\text{px}$) and lossy recompression ($Q < 60$) smooth sub-pixel Bayer CFA patterns and flatten ELA block differences.
3. **Screenshots / Non-Optical Media**: Lack physical camera silicon sensor noise.

### Planned Phase 2 Enhancements
1. **Local EfficientNet-B0 Fine-Tuning**: Train a dedicated binary classification head using FaceForensics++ and Celeb-DF datasets (`models/image_deepfake/training/train.py`).
2. **Neural Grad-CAM Activation Maps**: Replace client-side spatial gradient visualizer with backpropagated Grad-CAM once the local binary head is fine-tuned.
3. **Platt Scaling / Isotonic Calibration**: Fit calibration on validation split once a large-scale labelled benchmark dataset is ingested.
