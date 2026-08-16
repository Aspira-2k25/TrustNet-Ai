# Scan Management Service (services/scan_management)

Core intake and lifecycle service for scans.

## Endpoints

- `POST /scans/analyze` - synchronous direct image analysis
- `POST /scans/upload` - async file scan creation (image/audio/video)
- `POST /scans/text` - async text scan creation
- `POST /scans/url` - async URL scan creation
- `GET /scans/{scan_id}/status`
- `GET /scans/{scan_id}`
- `GET /scans`
- `GET /health`

## Responsibilities

- Validates uploaded media (extension, MIME, magic bytes, file limits).
- Sanitizes filenames and writes files under `storage_uploads/` fallback path.
- Persists scan records (SQLite by default in local dev).
- Publishes detection-requested events to Kafka topics by modality.
- Supports direct synchronous analyze path through `EfficientNetDetector`.

## Kafka Routing

- Image: `detection.requested.image_deepfake`
- Audio: `detection.requested.audio_deepfake`
- Video: `detection.requested.video_deepfake`
- Text: `detection.requested.scam_message`
- URL: `detection.requested.phishing`

## Runtime Defaults

- Port: `8002`
- DB default: `sqlite+aiosqlite:///./scan_dev.db`
- Kafka default: `localhost:9092`
- Storage fallback: `./storage_uploads`

## Run Locally

```bash
pip install -r services/scan_management/requirements.txt
uvicorn services.scan_management.app.main:app --port 8002 --reload
```

## Tests

```bash
python -m pytest services/scan_management/tests -v
```
