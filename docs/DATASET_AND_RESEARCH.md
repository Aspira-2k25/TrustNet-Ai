# TrustNet AI — Dataset, Model Versioning & Research Specification

**Baseline Marker**: `v1.0.0-frozen-baseline`  
**Runtime Operational Policy**: Production Inference is 100% self-contained and does NOT require any local dataset.

---

## 1. System Operational Modes & Dataset Separation

To maintain strict scientific integrity and architectural clarity, TrustNet defines three separate operating contexts:

| Operational Context | Dataset Required? | Active Models / Runtime | Description |
|---|---|---|---|
| **Production Inference** | **None** | Hugging Face ViT + 8 Local Forensic Analyzers + Fusion | Analyzes user-submitted media in real-time. No local dataset is read or needed. |
| **Benchmarking & Evaluation** | **Externally Supplied** | Evaluator Engine (`benchmark/`) | Evaluates the frozen baseline detector against a user-provided, labelled dataset. |
| **Future Model Training** | **Offline Dataset** | PyTorch AdamW Training Pipeline (`models/image_deepfake/training/`) | Offline fine-tuning of local binary heads (e.g. FF++, Celeb-DF v2). Currently inactive in production. |

> [!IMPORTANT]
> **EfficientNet Training Status**: EfficientNet training is currently **not** part of the production runtime. Production uses PyTorch ImageNet-1K pretrained `EfficientNet-B0` solely as a spatial feature backbone.

---

## 2. External Benchmark Dataset Specification

When evaluating TrustNet with the benchmark suite (`benchmark/benchmark_suite.py` or `benchmark/evaluate.py`), the dataset must be supplied as an external directory formatted as follows:

```
<external_benchmark_dir>/
├── real/                      # Verified authentic optical media (Ground Truth Label = 0)
│   ├── sample_camera_001.jpg
│   ├── sample_camera_002.png
│   └── ...
└── fake/                      # Manipulated media & AI-generated content (Ground Truth Label = 1)
    ├── midjourney_gen_001.jpg
    ├── deepfake_faceswap_002.png
    └── ...
```

### Supported Image Formats
- JPEG (`.jpg`, `.jpeg`) — Minimum recommended quality: $Q \ge 75$
- PNG (`.png`) — 8-bit/16-bit RGB/RGBA lossless
- WebP (`.webp`) — Lossless and lossy WebP
- Bitmap (`.bmp`) — Uncompressed raster
- TIFF (`.tif`, `.tiff`) — Uncompressed / LZW

### Binary Classification Ground Truth
- `0` / `REAL`: Authentic camera captures, unmanipulated photography, physical documents.
- `1` / `FAKE`: AI generative synthesis (Midjourney, Stable Diffusion, DALL-E, Flux, StyleGAN), deepfake facial swaps, morphing, splicing, inpainting.

---

## 3. Data Leakage & Near-Duplicate Screening Protocol

Before computing benchmark metrics, `benchmark/benchmark_suite.py` executes strict pre-flight leakage screening:

1. **Exact Duplicate Detection (Cryptographic Hashing)**:
   - Computes SHA-256 hash for every sample.
   - Identical hash collisions across `real` and `fake` or between partitions are flagged and rejected.

2. **Perceptual Near-Duplicate Screening (pHash)**:
   - Computes a 64-bit Average Perceptual Hash (pHash) per image.
   - Any pair with Hamming distance $D_H \le 3$ is flagged for manual review to prevent near-identical frames (e.g., adjacent frames from the same video clip) from contaminating splits.

3. **Zero-Identity Leakage Guarantee**:
   - For facial datasets, all frames belonging to subject identity $\text{ID}_k$ must reside strictly within a single partition (Train, Val, or Test).
   - Enforced by `verify_zero_identity_leakage()` in `models/image_deepfake/training/dataset.py`.

---

## 4. Recommended Metadata & Dataset Manifest Schema

For rigorous research publications and repeatable benchmarks, maintain a `manifest.json` alongside the image directory:

```json
{
  "benchmark_name": "TrustNet-External-Evaluation-v1",
  "created_at": "2026-08-16T00:00:00Z",
  "total_samples": 1000,
  "classes": {
    "real": {
      "count": 500,
      "sources": ["Nikon D850 RAW", "Canon EOS R5", "Sony A7IV", "Unsplash Authentic License"]
    },
    "fake": {
      "count": 500,
      "sources": {
        "diffusion": ["Midjourney v6", "SDXL 1.0", "Flux.1-dev", "DALL-E 3"],
        "face_manipulation": ["FaceForensics++ c23", "Celeb-DF v2", "DeepFaceLab"]
      }
    }
  },
  "partitions": {
    "train_ratio": 0.0,
    "val_ratio": 0.0,
    "test_ratio": 1.0
  }
}
```

---

## 5. Running the Benchmark Engine

```bash
# Run formal scientific evaluation with full metrics, ablation, and calibration
python benchmark/benchmark_suite.py /path/to/external_benchmark_dir

# Run fast CLI evaluator
python benchmark/evaluate.py --dataset-dir /path/to/external_benchmark_dir --threshold 50.0
```

### Standard Output Metrics
- **Accuracy, Precision, Recall (Sensitivity), Specificity, F1-Score**
- **False Positive Rate (FPR), False Negative Rate (FNR)**
- **Receiver Operating Characteristic Area (ROC-AUC)**
- **Precision-Recall Area (PR-AUC)**
- **Brier Score & Expected Calibration Error (ECE)**
- **Confusion Matrix** (`[[TN, FP], [FN, TP]]`)
- **Data Leakage Risk Status**
