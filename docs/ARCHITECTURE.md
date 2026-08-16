# TrustNet AI — System Architecture Specification

## 1. System Overview

**TrustNet AI** is a multimodal synthetic media verification platform designed to defend information integrity by detecting deepfakes and AI-generated content.

In Phase 1, the system is strictly focused on **Image Deepfake Detection**, providing end-to-end verification, spatial/frequency forensic evidence extraction, calibrated risk scoring ($0-100$), and visual explainability via **Grad-CAM**.

---

## 2. Global Architecture Flow

```mermaid
graph TD
    Client[React + Vite Frontend] -->|HTTP / Multipart| Gateway[API Gateway :8000]
    Gateway -->|JWT Auth / Reverse Proxy| ScanService[Scan Management Service :8002]
    ScanService -->|Store Binary| Storage[(Local / Quarantine Storage)]
    ScanService -->|Publish detection.requested.image_deepfake| Kafka{Apache Kafka 3.7 KRaft}
    Kafka -->|Consume Task| ImageService[Image Deepfake Worker Service :8003]
    ImageService -->|Inference & Grad-CAM| Model[EfficientNet-B0 + Spatial/Frequency Analyzers]
    Model -->|DetectionResult| ImageService
    ImageService -->|Publish detector.image_deepfake.completed| Kafka
    Kafka -->|Consume Result| TrustEngine[Trust Engine Service :8004]
    TrustEngine -->|Compute Trust Score| TrustEngine
    TrustEngine -->|Update Status| ScanService
    Client -->|Poll GET /scans/{id}/status| Gateway
```

---

## 3. Communication Protocol: Kafka-First

TrustNet AI uses **Apache Kafka 3.7 (KRaft mode)** as its primary asynchronous message broker for detector jobs.

### Active Image Topics
- `detection.requested.image_deepfake`: Emitted by Scan Management when an image scan is created.
- `detector.image_deepfake.completed`: Emitted by the Image Deepfake Service when inference and explainability processing finish.

### Topic Schema
All messages conform to the typed `EventEnvelope` defined in `shared.schemas.events`:
```json
{
  "event_id": "evt-b1a9c3d4",
  "event_type": "detection.requested.image_deepfake",
  "timestamp": "2026-08-16T03:00:00Z",
  "producer": "scan-management-service",
  "version": "1.0.0",
  "data": {
    "scan_id": "scan-ff-c23-0182",
    "media_path": "storage_uploads/quarantine/image/sample.jpg",
    "modality": "image"
  }
}
```

---

## 4. Image Deepfake Detection Architecture

The Image Deepfake detection pipeline consists of:

1. **Security Intake & Preprocessing (`models.image_deepfake.preprocessing`)**:
   - MIME type verification, magic-byte inspection, resolution normalization (224x224 RGB), ImageNet mean/std normalization.
   - Face landmark detection (MTCNN / Haar Cascade).
2. **Primary Vision Feature Classifier (`models.image_deepfake.inference`)**:
   - **EfficientNet-B0** convolutional neural network pretrained on ImageNet and fine-tuned on benchmark deepfake datasets (FaceForensics++, Celeb-DF v2).
   - Produces raw probability $P(\text{REAL})$ (`probability_of_negative_class`).
3. **Risk Normalization**:
   - Transforms native probability to unified downstream Risk Score:
     $$\text{risk\_score} = \text{round}((1.0 - \text{native\_score}) \times 100)$$
4. **Forensic Analyzers**:
   - **Spatial Feature Classifier**: Convolutional feature divergence.
   - **FFT High-Frequency Residual Analyzer**: 2D Discrete Fourier Transform spectrum inspection to detect periodic GAN grid artifacts.
   - **Error Level Analysis (ELA)**: 8x8 DCT compression error consistency check.
   - **Face Landmark & Boundary Warping (Face X-Ray)**: Face boundary blending analysis.
     > **Face vs. Non-Face Policy**: When an image has no detectable human face, face-specific analyzers (e.g. Face X-Ray) are explicitly **SKIPPED** with an audit note `"No human facial landmark identified; skipped to prevent false positives"`. Whole-image spatial and frequency analyzers continue normally.
5. **Explainability Engine (`models.image_deepfake.explainability`)**:
   - **Grad-CAM** computes gradient attribution maps on EfficientNet layer 4 feature maps, producing high-resolution saliency overlays.

---

## 5. Trust Engine & Scoring Contract

The Trust Engine aggregates detector outputs into a normalized Trust Score Result:
- **Trust Risk Score**: $0$ (Completely Authentic) to $100$ (Critical Risk / Deepfake).
- **Risk Level**: `LOW` (0-24), `MEDIUM` (25-49), `HIGH` (50-74), `CRITICAL` (75-100).
- **Evidence Breakdown**: Structured list of `EvidenceItem` records with feature names, weights, and human-readable observations.
- **Natural Language Explanation**: Clear synthesis of model confidence and forensic signals.

---

## 6. Frontend Architecture (React + Vite + Tailwind CSS)

The user interface is a high-productivity security workstation designed for forensic analysts and researchers:
- **Dashboard**: Telemetry metrics, recent scans, risk distribution, status filters.
- **Image Scan Intake**: Drag & drop zone, file validation (JPEG, PNG, WebP $\le$ 10MB), real-time pipeline execution stepper.
- **Forensic Inspection Workspace**:
  - Primary Verdict Banner (`AUTHENTIC`, `SUSPICIOUS`, `AI_GENERATED`) with SVG Risk Gauge.
  - Saliency Heatmap Studio (Grad-CAM overlay, 0-100% opacity slider, zoom & reset, side-by-side view).
  - Forensic Evidence Contribution Bars & Notes.
  - Forensic Analyzers Audit (Status of each detector and non-face skip reasoning).
  - Technical Provenance Metadata (Model ID, Version, Preprocessing, Latency, Native score).
