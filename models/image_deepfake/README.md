# TrustNet AI — Image Deepfake Detection: Data Science & Mathematical Specification

## 1. Architectural Overview & Mathematical Thesis

Traditional deepfake detection systems rely solely on end-to-end convolutional neural networks (CNNs) or Vision Transformers (ViTs). While achieving high accuracy on specific benchmark datasets, pure learned models suffer from **out-of-distribution failure, concept drift, adversarial sensitivity, and false-positive fragility** on camera artifacts or digital artwork.

TrustNet AI implements **Physics-Informed Evidential Fusion**: coupling deep neural spatial representations with deterministic mathematical invariants derived from optical physics, digital signal processing, sensor electronics, photogrammetry, and covert payload steganography.

```
                              ┌────────────────────────────────────────┐
                              │           Input Image Matrix           │
                              │           I(x,y) ∈ ℝ^{H × W × 3}       │
                              └───────────────────┬────────────────────┘
                                                  │
                ┌─────────────────────────────────┴─────────────────────────────────┐
                ▼                                                                   ▼
┌───────────────────────────────┐                                   ┌───────────────────────────────┐
│     Semantic Scene Engine     │                                   │      Face Detection & Crop    │
│    SceneContextAnalyzer(I)    │                                   │       FaceAnalyzer(I)         │
└───────────────┬───────────────┘                                   └───────────────┬───────────────┘
                │ Domain D ∈ {Portrait, Art, Arch, Nature, Object}                  │ has_face ∈ {True, False}
                └─────────────────────────┬─────────────────────────────────────────┘
                                          │
    ┌─────────────────────────────────────┼─────────────────────────────────────┐
    │                                     │                                     │
    ▼                                     ▼                                     ▼
┌─────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────────┐
│   Learned Neural Layer  │   │  Micro-Forensics Layer  │   │ Physical Optics & Stego │
├─────────────────────────┤   ├─────────────────────────┤   ├─────────────────────────┤
│ • Vision Transformer    │   │ • 2D Fourier (FFT)      │   │ • Corneal Parallax      │
│   (ViT dima806 / Local) │   │ • Sub-Pixel Bayer CFA   │   │ • 3D Vanishing Geometry │
│ • EfficientNet-B0       │   │ • Gabor Filter Bank     │   │ • Error Level Analysis  │
│   (1280-dim Backbone)   │   │ • PRNU Sensor Noise     │   │ • Face X-Ray Seams      │
│ • Local AI Vision LM    │   │ • Social Re-Compression │   │ • Watermark Icon        │
│   (Qwen3-VL via Studio) │   │   (8x8 DCT Grid)        │   │ • Covert Steganography  │
└───────────┬─────────────┘   └───────────┬─────────────┘   └───────────┬─────────────┘
            │                             │                             │
            │ s_learned                   │ s_micro                     │ s_physical
            └─────────────────────────────┼─────────────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │    Cross-Domain Evidential Fusion      │
                      │  A_weighted = ∑ (s_i · w_i) / ∑ w_i    │
                      │  + Multi-Vector Corroboration (N ≥ 2)  │
                      │  + Two-Way Contradiction Filter        │
                      │  + Zero False-Positive Calibration     │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │   Calibrated Risk Score & Verdict      │
                      │   Risk ∈ [0, 100], Verdict ∈ 4 Levels  │
                      └────────────────────────────────────────┘
```

---

## 2. Complete 16-Analyzer Forensic Inventory

| # | Analyzer / Module | Category | Primary Method & Math | Role in TrustNet | Source File |
|---|---|---|---|---|---|
| **1** | **EfficientNet-B0 Backbone** | `primary_ml` | 1280-dim deep convolutional spatial variance | Extracts multi-scale visual representations; base for Grad-CAM explainability heatmaps. | `inference/efficientnet_detector.py` |
| **2** | **Vision Transformer (ViT)** | `primary_ml` | Multi-head self-attention on $16 \times 16$ patches | Evaluates patch relationships to classify facial deepfakes vs authentic captures (`dima806`). | `inference/huggingface_client.py` |
| **3** | **Local ViT Offline Detector** | `primary_ml` | Local `transformers` pipeline (CPU/CUDA) | Zero-cost, rate-limit-proof offline fallback when cloud HF API is unavailable or credit-depleted. | `inference/local_vit_detector.py` |
| **4** | **Local AI Vision (Qwen3-VL)** | `local_vision` | Multimodal semantic reasoning (LM Studio) | Analyzes fine textures, anatomy boundaries, and lighting anomalies; generates plain-English debriefs. | `inference/lm_studio_vision_client.py` |
| **5** | **Covert Steganography Scanner** | `steganography` | EOF trailer inspection & Westfeld $\chi^2$ PoVs | Detects hidden archives (ZIP, RAR, 7z, PDF, EXE) and sequential/saturated LSB bitstreams. | `forensics/steganography_analyzer.py` |
| **6** | **2D Fast Fourier Transform (FFT)** | `frequency` | Azimuthal radial integration & $1/f^\alpha$ decay | Identifies non-optical high-frequency energy spikes and GAN/diffusion periodic lattice grids. | `forensics/frequency_analyzer.py` |
| **7** | **Sub-Pixel Bayer CFA Analyzer** | `micro_forensics` | Demosaicing residual error & kurtosis $\kappa$ | Verifies physical sensor color filter array micro-edge continuity vs synthetic diffusion upscaling. | `forensics/pixel_morphing_analyzer.py` |
| **8** | **Multi-Scale Gabor Filter Bank** | `texture_forensics` | 4 orientations ($\theta$) $\times$ 3 scales ($\lambda$) entropy | Measures texture orientation Shannon entropy $H_\theta$ to detect unnatural synthetic smoothing. | `forensics/gabor_analyzer.py` |
| **9** | **Error Level Analysis (ELA)** | `compression` | JPEG DCT $Q=90$ quantization error variance | Flags regional compression disparities indicative of digital splicing and inpainting. | `forensics/ela_analyzer.py` |
| **10** | **Sensor Pattern Noise (PRNU)** | `sensor_forensics`| 4-neighbor spatial median noise residual | Evaluates camera silicon sensor noise kurtosis $\kappa_W$ vs clean synthetic generation. | `forensics/noise_analyzer.py` |
| **11** | **Face Landmark Boundary (X-Ray)**| `face_forensics` | Multi-angle rotation (+/-25°) edge gradient | Detects blending seam step gradients along jawline/hairline from face-swap deepfakes. | `forensics/face_analyzer.py` |
| **12** | **Corneal Specular Reflection** | `physics_engine` | Specular centroid parallax vectors $\cos \theta$ | Confirms 3D physical consistency of environmental lighting across both eyes. | `forensics/physics_eye_reflection_analyzer.py` |
| **13** | **3D Vanishing Geometry Support** | `physics_engine` | Probabilistic Hough transform perspective lines | Detects structural perspective line warping and melting in synthetic architecture. | `forensics/geometry_physics_analyzer.py` |
| **14** | **Semantic Scene Context** | `semantic` | Palette quantization & edge density ratio | Classifies media into 5 scene domains; calibrates sensor weights to prevent false positives. | `forensics/scene_analyzer.py` |
| **15** | **Provenance & Metadata Scanner** | `metadata` | EXIF, XMP, & info chunk signature parsing | Scans for 50+ known generative platform signatures (Midjourney, DALL-E, SDXL, ComfyUI). | `forensics/metadata_analyzer.py` |
| **16** | **Social Re-Compression Analyzer** | `compression` | 8x8 DCT grid blockiness ratio | Detects social re-compression (e.g., WhatsApp) and scales down fragile physical heuristics. | `forensics/recompression_analyzer.py` |

---

## 3. Steganography & Covert Payload Forensic Engine

The steganography engine (`forensics/steganography_analyzer.py`) provides covert data auditing with **mathematically enforced zero false positives on genuine images**:

### 3.1 End-of-File (EOF) Trailer Injection
Standard image formats define rigid end-of-file terminator markers:
- **JPEG**: `0xFF 0xD9` (EOI - End of Image)
- **PNG**: `49 45 4E 44 AE 42 60 82` (`IEND` chunk + 4-byte CRC)
- **GIF**: `0x3B` (GIF Trailer)

Any binary bytes appended past these markers do not alter visual rendering in standard image viewers, but represent hidden data channels.
1. The analyzer scans the trailer after the EOF marker.
2. Minor trailing spaces/null bytes ($\le 16$ bytes) used for filesystem cluster alignment are safely ignored.
3. Magic signatures are matched against:
   - `PK\x03\x04`: ZIP Archive
   - `Rar!\x1a\x07`: RAR v4 / v5 Archive
   - `7z\xbc\xaf\x27\x1c`: 7-Zip Archive
   - `%PDF-`: Embedded PDF Document
   - `MZ`: Windows Executable / DLL
   - `\x7fELF`: Linux Binary
   - `\x1f\x8b`: GZIP Stream
   - `OPENSTEGO`: OpenStego Container
4. Plaintext ASCII strings ($\ge 12$ characters) are extracted and presented in the report preview.

### 3.2 Least Significant Bit (LSB) Statistical Attack
1. **Direct Sequential ASCII Extraction**: Checks the first 512 pixels (192 bytes) of LSB bitplanes for sequential plaintext strings (e.g. `FLAG{`, `password`, URLs).
2. **Westfeld's Chi-Square ($\chi^2$) Pairs of Values (PoVs) Test**:
   - In natural photography, values $2k$ and $2k+1$ have asymmetric frequency counts due to natural illumination gradients.
   - Saturated random LSB embedding equalizes these pairs: $h(2k) \approx h(2k+1)$.
   - Evaluates:
     $$\chi^2 = \sum_{k=0}^{127} \frac{\left(h(2k) - \frac{h(2k) + h(2k+1)}{2}\right)^2}{\frac{h(2k) + h(2k+1)}{2}}$$
   - **Zero False-Positive Gates**:
     - Image pixel count must be $\ge 4096$.
     - Standard deviation of luminance must be $\ge 16.0$ (flat canvas/drawings automatically bypass test).
     - Number of degrees of freedom must be $\ge 24$.
     - $\chi^2$ survival function $p$-value must exceed $0.9995$.
     - Bitplane 0 Shannon entropy must exceed $0.998$ with a balanced $0/1$ ratio ($0.48 \le p_0 \le 0.52$).

---

## 4. Multi-Signal Evidential Fusion & Calibration

### 4.1 Evidential Corroboration Ladder
Rather than computing an uncalibrated linear average, signals are evaluated through a hierarchical corroboration ladder:

1. **Covert Payload Override**: If verified steganography/EOF injection exists, anomaly is set to $\ge 0.85$.
2. **Neural Face Specialist**: If ViT certifies synthetic human face ($\ge 70\%$), anomaly $\ge 0.78$ (or $\ge 0.86$ if corroborated by physical checks).
3. **Authentic Camera Portrait**: When ViT certifies real ($\ge 80\%$) on a human face and zero physical anomalies exist, anomaly is clamped to $\le 0.16$ (prevents shadow/glasses false positives from flipping camera photos).
4. **Physical Corroboration**: If $\ge 2$ independent physical domains flag anomalies, anomaly $\ge 0.74$.
5. **Human Digital Artwork Calibration**: When `SceneContextAnalyzer` verifies 2D hand-drawn artwork (`anime_illustration`), boundary noise is suppressed and clean vector ink is calibrated to $\le 0.15$.
6. **Watermark Icon Corroboration**: Evaluates pointedness and aspect solidity in bottom corners; participates as a standard corroborating vote (no single-point override on verified real photos).

### 4.2 Two-Way Contradiction Handling
If learned neural models and physical sensors produce contradictory evidence on a human subject (e.g., ViT indicates 99% real but two physical sensors flag anomalies), a contradiction flag is raised:
$$\mathbf{Verdict} \leftarrow \mathbf{UNCERTAIN}, \quad \text{Risk} \in [40.0, 60.0]$$

---

## 5. Dual-Mode Execution: Fast Scan vs Local Vision Reasoning

TrustNet supports two operational modes via the `enable_explanation` parameter:

| Feature | Fast Scan (`enable_explanation=False`) | Deep Explanation (`enable_explanation=True`) |
|---|---|---|
| **Execution Latency** | **~1.0 to 1.5 seconds** | ~15 to 35 seconds (CPU mode) |
| **Analyzers Evaluated** | All 15 physical/stego/metadata analyzers + Neural ViT | All 15 physical/stego/metadata analyzers + Neural ViT + Local Qwen3-VL |
| **Hardware Requirement** | Standard CPU / Laptop | Local LM Studio instance (`http://localhost:1234/v1`) |
| **Image Preprocessing** | Full resolution native byte arrays | Resolution-capped 256px JPEG (<50KB) for lightweight vision inference |
| **UI Telemetry** | Full ELA, CFA, Radar, and 16-Module telemetry list | Full telemetry list + Plain-English Visual Reasoning Debrief card |

---

## 6. Directory Structure & File Map

```
TrustNet-Ai/models/image_deepfake/
├── README.md                                 # Complete scientific specification (this file)
├── explainability/
│   └── grad_cam.py                           # PyTorch layer-4 activation map extractor
├── forensics/
│   ├── steganography_analyzer.py             # EOF trailer injection & Westfeld Chi-Square LSB engine
│   ├── frequency_analyzer.py                 # 2D FFT radial decay (1/f^alpha) analyzer
│   ├── pixel_morphing_analyzer.py            # Sub-pixel Bayer CFA demosaicing continuity
│   ├── gabor_analyzer.py                     # Multi-scale Gabor filter bank texture analyzer
│   ├── ela_analyzer.py                       # JPEG DCT quantization Error Level Analysis
│   ├── noise_analyzer.py                     # PRNU camera sensor pattern noise residual
│   ├── face_analyzer.py                      # Multi-pass Haar cascade face seam analyzer
│   ├── physics_eye_reflection_analyzer.py    # Corneal specular reflection parallax vectors
│   ├── geometry_physics_analyzer.py          # 3D Hough line structural vanishing perspective
│   ├── scene_analyzer.py                     # Color quantization & semantic domain router
│   ├── metadata_analyzer.py                  # EXIF/XMP provenance signature scanner
│   ├── recompression_analyzer.py             # 8x8 DCT grid blockiness analyzer
│   └── watermark_analyzer.py                 # Bottom-corner convexity defect watermark detector
├── inference/
│   ├── efficientnet_detector.py              # Master multi-vector evidential fusion engine
│   ├── huggingface_client.py                 # Cloud ViT client (dima806)
│   ├── local_vit_detector.py                 # Offline local transformers fallback
│   └── lm_studio_vision_client.py            # Local vision reasoning client (Qwen3-VL)
└── tests/
    ├── test_lm_studio_fusion.py              # Tests for local vision fusion & contradiction
    ├── test_local_vit_and_dual_ml.py         # Tests for local ViT and cloud fallback
    └── test_watermark_false_positive_hotfix.py# Tests for watermark shape filtering
```

---

## 7. API Reference

### Synchronous Scan Endpoint
`POST /scans/analyze` (Scan Management Service: Port 8002 / API Gateway: Port 8000)

**Form Parameters:**
- `file`: Multipart image file (`image/jpeg`, `image/png`, `image/webp`).
- `enable_explanation`: Boolean (`true` to invoke LM Studio vision reasoning; `false` for ~1s Fast Scan).

**Response Schema (`DetectionResult`):**
```json
{
  "scan_id": "scan-e5c096d91f",
  "verdict": "AUTHENTIC",
  "risk_score": 12.5,
  "confidence": 0.88,
  "has_face": true,
  "explanation": "Authentic photograph verified: natural optical lens frequency roll-off, homogeneous single-source compression, and seamless facial skin tone transitions confirmed.",
  "metadata": {
    "scene_label": "Photographic Portrait / Human Subject",
    "stego_detected": false,
    "stego_payload_type": null,
    "stego_payload_size": 0,
    "lm_studio_status": "SKIPPED"
  },
  "analyzers": [
    {
      "name": "Covert Steganography: LSB & File Trailer Scanner",
      "category": "steganography_forensics",
      "status": "APPLIED",
      "finding": "Clean (No hidden steganographic payload detected)."
    }
  ]
}
```
