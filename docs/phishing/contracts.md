# Phase 1 — phishing platform contract

## Request and completion

Existing Gateway forwards authenticated POST `/api/v1/scans/url` to Scan Management. Intake currently allows 4–2048 characters; the offline parser's 8192 maximum does not expand the public API. Scan Management creates a QUEUED URL scan, commits it, then publishes canonical `DetectionRequestedEvent` to `Topics.DETECTION_REQUESTED_PHISHING` (the URL alias resolves to the same topic). Kafka key is scan_id. Module is `phishing`, payload.url retains the URL, schema_version must match the shared version, timestamp is UTC.

Phishing consumes `detection.requested.phishing` and emits `DetectorCompletedEvent` on `detector.phishing.completed`, keyed by the same scan_id. Exhausted/invalid requests use the corresponding `.dlq` topic. Model code implements the unchanged BaseDetector.predict interface and imports no Kafka/database/FastAPI client. The service adapter rejects another module and an unsupported schema version.

Shared DetectionResult uses phishing probability as native_score with probability_of_positive_class semantics, risk_score=round(100*p), and label phishing/legitimate at a validation-selected threshold. Unknown/unavailable is not a safe verdict. Failed results require error_code; successful and partial results have no error fields. Do not populate image-only verdict/face fields. Observations and model attribution are distinct. Baselines report partial coverage and unavailable confidence; the hybrid must report actual branch versions and calibrated status.

## Lifecycle and ownership

Scan lifecycle is separate from detector StatusEnum. URL intake already uses QUEUED rather than premature SUCCESS. Processing is optional when explicitly persisted; terminal status follows a durable completion. Scan Management owns PostgreSQL scan status and authenticated result access. Phishing should own MongoDB detector/evidence persistence; Redis is optional acceleration; MinIO/S3 holds datasets/artifacts.

Worker ordering must be: validate association; retrieve durable prior completion or infer; persist result and reusable completion; publish completion; commit request offset. Publication failure must retain the same reusable completion/event ID. Duplicate deliveries cannot contribute twice. Conflicting payloads for the same scan must be rejected/DLQ. Mongo persistence plus Kafka publication require recovery; neither should be claimed atomic.

## Current integration audit (12 October 2026)

- Scan Management already publishes URL requests and persists QUEUED before dispatch.
- `services/scan_management/app/completion_consumer.py` currently recognizes only image/text modality mappings and subscribes only to image/scam completions. Add a URL→phishing mapping and phishing completion subscription in the integration phase without changing existing modality behavior.
- Trust Engine already subscribes to phishing completions; its current process-memory duplicate buffer is not a durable guarantee across restarts. Verify restart behavior before accepting reliability gates.
- Existing shared worker uses SQLite completion caching, not the planned MongoDB detector repository. Reuse requires documenting storage policy or implementing the prescribed repository.
- Frontend phishing view still fabricates data; replace it with Gateway submission and authenticated polling during Phase 5. Never demonstrate its mock findings as real inference.
- The new internal phishing FastAPI app exposes health/readiness only. Health indicates process liveness; readiness requires a loaded artifact. No browser inference route is added.

Phase 1 contract is documented; consumer/storage/rollback agreement and implementation verification remain open.
