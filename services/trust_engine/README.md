# Trust Engine Service (services/trust_engine)

Fuses detector outputs into a final trust-risk score.

## Endpoints

- `POST /fuse` - fuse one or more detection results
- `GET /scores/{scan_id}` - fetch fused score
- `GET /health`

## Responsibilities

- Background Kafka consumer for detector completion topics.
- Buffers scan-level results and fuses them using fusion engine weights.
- Stores fused scores in in-memory repository (`ScoreRepository`).
- Publishes `trust_score.generated` when Kafka producer is available.

## Kafka Topics

Consumes:

- `detector.image_deepfake.completed`
- `detector.audio_deepfake.completed`
- `detector.video_deepfake.completed`
- `detector.phishing.completed`
- `detector.scam_message.completed`
- `detector.fake_review.completed`
- `detector.osint.completed`

Publishes:

- `trust_score.generated`

## Runtime Defaults

- Port: `8004`
- Kafka default: `localhost:9092`
- Consumer group: `trustnet_trust_engine_group`

## Run Locally

```bash
pip install -r services/trust_engine/requirements.txt
uvicorn services.trust_engine.app.main:app --port 8004 --reload
```

## Tests

```bash
python -m pytest services/trust_engine/tests -v
```
