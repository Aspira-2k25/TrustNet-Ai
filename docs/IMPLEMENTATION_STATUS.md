# TrustNet AI — Implementation Status & Architecture Audit

## Current Architecture & Implementation Matrix

| Component / Subsystem | Status | Implementation Details |
|---|---|---|
| **API Gateway** (`gateway/`) | **IMPLEMENTED** | FastAPI reverse proxy, strictly enforced JWT auth guard (`verify_token`), centralized CORS configuration, request routing to downstream microservices via service tokens / headers. |
| **Auth Service** (`services/auth/`) | **IMPLEMENTED** | Password hashing (bcrypt), SQLAlchemy async engine (SQLite dev / PostgreSQL prod), strict JWT access/refresh token generation, no production mock bypass. |
| **Scan Management Service** (`services/scan_management/`) | **IMPLEMENTED** | Multi-step ingestion validation (MIME, magic bytes, configurable 10MB image default), quarantine storage, threadpool async ML offloading, Kafka async producer (`detection.requested.image_deepfake`). |
| **Image Deepfake Service** (`services/image_deepfake/`) | **IMPLEMENTED** | Kafka consumer worker, threadpool-isolated EfficientNet-B0 inference, Hugging Face ViT with existing local fallback, local ELA, Gabor noise, ImageNet-class Grad-CAM diagnostic (not fused deepfake attribution), LM Studio vision fusion, Kafka result publisher. |
| **Trust Score Engine** (`services/trust_engine/`) | **IMPLEMENTED** | Kafka consumer for completed detections, normalized & bounded risk calibration ($0-100$), evidence synthesis, contradiction resolution, fallback handling. |
| **Shared Core Library** (`shared/`) | **IMPLEMENTED** | Pydantic v2 schemas (`APIResponse`, `DetectionResult`, `EventEnvelope`), strict JWT verification with algorithm validation and production mock rejection, centralized base settings, structured logging. |
| **Frontend Application** (`frontend/`) | **IMPLEMENTED** | React 19 + TypeScript + Vite, modularized API client (`frontend/src/services/api/`) communicating strictly via API Gateway (`VITE_API_GATEWAY_URL`), no direct microservice bypass. |
| **Video Deepfake Service** (`services/video_deepfake/`) | **PLACEHOLDER** | Planned for Phase 2: Frame sequence extraction & 3D-CNN / LSTM temporal forensic detection. |
| **Audio Deepfake Service** (`services/audio_deepfake/`) | **PLACEHOLDER** | Planned for Phase 3: RawNet2 / SpecNet acoustic feature extraction for synthetic voice detection. |
| **Phishing & Scam URL Detection** | **PLACEHOLDER** | Planned for Phase 4: Domain reputation, lexical analysis, and NLP page classification. |
| **Infrastructure** (`docker-compose.yml`) | **IMPLEMENTED** | Apache Kafka 3.7 (KRaft mode), PostgreSQL, Redis, MongoDB, MinIO with environment variable substitution, dedicated bridge network (`trustnet_net`), and container healthchecks. |
| **Automated Test Suite** | **IMPLEMENTED** | Historical pass/coverage claims are not current measurements. The 2026-10-11 run includes pre-existing failures and obsolete assertions; see the external QA handoff. |

---

## Security & Architectural Hardening Summary
1. **Frontend Isolation**: Browser communicates exclusively through the API Gateway on port 8000; all direct calls to ports 8001–8004 removed.
2. **Strict Auth Verification**: Mock tokens (`mock_jwt_`, `developer_token`) are strictly forbidden unless `ENVIRONMENT=dev` AND `ALLOW_MOCK_AUTH=true`. In `production`, mock tokens and insecure placeholder secrets are unconditionally rejected.
3. **CORS Hardening**: Backend services reject wildcard `*` with credentials in production, enforcing explicit origin whitelists via `CORS_ALLOWED_ORIGINS`.
4. **Credential Security**: Passwords in `docker-compose.yml` use environment substitution (`${POSTGRES_PASSWORD}`, `${MINIO_ROOT_PASSWORD}`); `.env.example` contains only documentation placeholders.
5. **Upload & Path Traversal Protection**: Configurable 10MB default image file size limit, PIL magic byte header verification, safe filename normalization, and directory traversal defense in storage resolvers.
6. **Async Concurrency**: Synchronous CPU-intensive forensic inference is offloaded via `run_in_threadpool` to prevent blocking FastAPI's async event loop.

Scam message service is implemented on port 8005 with a selected calibrated DistilBERT three-class SMS classifier with CPU serving. DistilBERT was actually fine-tuned locally on MX450; selected by validation macro-F1 and deployed with CPU serving. Independent curated-source performance is weak; scope is English SMS screening.
