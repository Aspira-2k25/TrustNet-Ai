# Scan Management Service (`services/scan_management/`)

## 📌 Service Overview
The `scan_management_service` acts as the secure intake gate and lifecycle manager for all media analysis scans.

---

## 🛡️ Security Validation Pipeline (Master Spec §14)
Every file upload passes through a rigorous 4-stage validation pipeline before acceptance:
1. **Extension Whitelisting**: Verifies extension matches allowable image, audio, or video types.
2. **MIME Type Inspection**: Verifies `Content-Type` against allowed modalities.
3. **Magic Byte Verification**: Inspects leading binary bytes to ensure the actual file format matches declared type (prevents disguised executable uploads).
4. **Filename Sanitization**: Replaces original filename with a cryptographically secure UUID (`<uuid>.<ext>`) stored in quarantine object storage prefix.

---

## 🔄 Kafka Event Dispatch
Upon acceptance, the service:
1. Persists initial scan record in PostgreSQL (`status: PENDING`).
2. Publishes `DetectionRequestedEvent` to Kafka topic `detection.requested.image_deepfake` partitioned by `scan_id`.
3. Returns `202 Accepted` with `scan_id` to client.

---

## 🧪 Testing
```bash
python -m pytest services/scan_management/tests/ -v
```
