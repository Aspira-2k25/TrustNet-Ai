# TrustNet AI — Repository File Structure & Placement Guide

## 1. Top-Level Directory Tree

```
TrustNet/
├── README.md                  # Primary developer onboarding guide
├── docker-compose.yml         # Kafka 3.7 KRaft and core service containers
├── Makefile                   # Monorepo task automation
├── pytest.ini                 # Global pytest configuration
│
├── benchmark/                 # Formal evaluation, leakage audit & ablation engine
│   ├── benchmark_suite.py     # Canonical evaluation & calibration protocol
│   ├── evaluate.py            # CLI dataset evaluation tool
│   ├── baseline_manifest.json # v1.0.0-frozen-baseline specification
│   └── leakage_report.json    # Data leakage & duplicate screening protocol
│
├── docs/                      # Centralized documentation
│   ├── ARCHITECTURE.md        # Global system & Kafka architecture
│   ├── DEVELOPMENT.md         # Developer setup & coding standards
│   ├── FILE_STRUCTURE.md      # This file
│   ├── IMPLEMENTATION_STATUS.md # Active status & checklist
│   ├── DATASET_AND_RESEARCH.md# ML datasets, metrics & research notes
│   ├── TrustNet_AI_Master_Technical_Specification.md # Official master spec
│   └── TrustNet_AI_Engineering_Blueprint.md          # Official engineering blueprint
│
├── frontend/                  # React 18 + Vite + Tailwind CSS UI
│   ├── src/
│   │   ├── components/        # Navbar, TrustScoreGauge, SpatialSaliencyViewer, EvidenceBadges, ForensicRadarChart
│   │   ├── views/             # LandingView, DashboardView, ScanUploadView, ReportView, Auth
│   │   ├── services/api.ts    # REST API & mock simulation client
│   │   ├── types/index.ts     # TypeScript forensic schemas
│   │   ├── App.tsx            # Main application router & view controller
│   │   └── main.tsx           # React entry point
│   ├── package.json
│   └── vite.config.ts
│
├── gateway/                   # API Gateway (Reverse proxy & CORS)
│   ├── app/
│   │   ├── main.py            # FastAPI entry point & CORS
│   │   ├── config.py          # Port & routing configuration
│   │   └── proxy.py           # HTTP forwarding handlers
│   └── requirements.txt
│
├── models/                    # Pure ML Model Frameworks (PyTorch)
│   └── image_deepfake/        # Image Deepfake detector
│       ├── configs/           # YAML model hyperparameters
│       ├── preprocessing/     # Image validation & tensor transforms
│       ├── architecture/      # EfficientNet-B0 backbone definition
│       ├── forensics/         # Gabor, FFT, ELA, PRNU, Face X-Ray, CFA, Optics, Geometry, Metadata, Scene
│       ├── inference/         # Pure PyTorch detector wrapper & Hugging Face client
│       ├── explainability/    # Grad-CAM saliency computation
│       ├── training/          # Dataset loaders (zero identity leak) & train loop
│       ├── tests/             # Forensic & PyTorch unit tests
│       └── README.md          # Model module documentation
│
├── services/                  # Microservice Worker Services
│   ├── auth/                  # JWT Authentication & User Management
│   ├── scan_management/       # Scan ingestion, quarantine storage & Kafka producer
│   ├── image_deepfake/        # Kafka consumer worker & inference runtime
│   └── trust_engine/          # Risk score calibration & evidence aggregation
│
├── shared/                    # Monorepo Shared Core Library
│   ├── auth/                  # JWT token validation helpers
│   ├── config/                # Base pydantic settings
│   ├── constants/             # Topics, status codes, native score semantics
│   ├── interfaces/            # DetectorBase abstract interface
│   ├── logging/               # Structured log formatting
│   ├── schemas/               # EventEnvelope, DetectionResult, EvidenceItem
│   ├── utils/                 # UUID & timestamp generators
│   └── tests/                 # Shared library unit tests
│
└── tests/                     # Monorepo End-to-End Test Suite
    └── e2e/
        └── test_full_scan_pipeline.py # End-to-end integration test
```

---

## 2. File Placement Rules

1. **Pure ML Code**: Always place inside `models/{modality}/`. Never import FastAPI or Kafka inside `models/`.
2. **Service Workers**: Place inside `services/{service_name}/`. Service code wraps ML models, manages Kafka subscriptions, and exposes health endpoints.
3. **Shared Schemas**: When a contract is used by multiple services or models, define it once in `shared/schemas/`.
4. **Documentation**: All high-level documentation belongs in `docs/`. Module-level details belong in `models/{modality}/README.md` or `services/{service}/README.md`.
