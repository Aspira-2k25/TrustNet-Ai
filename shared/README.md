# Shared Core & Foundation (`shared/`)

## 📌 Overview
The `shared/` package contains cross-cutting contracts, Pydantic schemas, constants, logging utilities, and interfaces used across all microservices and ML models.

---

## 📁 Package Modules
- `shared/auth/`: Zero-network-call JWT verification helper (`verify_token.py`).
- `shared/config/`: `BaseSettings` base class for Pydantic configuration.
- `shared/constants/`: Enums for `ModuleEnum`, `StatusEnum`, `NativeScoreSemanticsEnum`, and Kafka `Topics`.
- `shared/interfaces/`: Abstract base classes (`BaseDetector`).
- `shared/logging/`: Structured JSON log formatter and logger setup (`get_logger`).
- `shared/schemas/`: Universal contracts (`DetectionResult`, `APIResponse`, `Events`, `EvidenceItem`).
- `shared/utils/`: Standard UUID and ID generator helpers (`ids.py`).

---

## 🧪 Testing
```bash
python -m pytest shared/tests/ -v
```
