# Image Deepfake Service (services/image_deepfake)

Worker and direct API service for image-forensics inference.

## Endpoints

- `POST /detect/file` - run detector on uploaded image
- `POST /detect/key` - run detector by storage key
- `GET /health`

## Responsibilities

- Runs multi-signal image forensic detection via `EfficientNetDetector`.
- Can consume Kafka events in background thread when enabled.
- Publishes detector-completed events through worker pipeline.

## Kafka

- Consumes: `detection.requested.image_deepfake`
- Consumer group default: `trustnet_image_deepfake_group`
- Toggle: `ENABLE_KAFKA_CONSUMER` (default true)

## Runtime Defaults

- Port: `8003`
- Kafka default: `localhost:9092`
- Storage fallback: `./storage_uploads`

## Run Locally

```bash
pip install -r services/image_deepfake/requirements.txt
uvicorn services.image_deepfake.app.main:app --port 8003 --reload
```

## Tests

```bash
python -m pytest services/image_deepfake/tests -v
```
