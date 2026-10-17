# Phishing service foundations

Start the internal app from repository root:

```powershell
$env:PHISHING_MODEL_MANIFEST = 'C:\absolute\trusted\bundle\lr.json'
python -m uvicorn services.phishing_url.app.main:app --port 8007
```

Use `requirements-runtime.txt` for the baseline worker and `requirements.lock` for the local training environment. `scripts/start-phishing-infrastructure.ps1` selects the hybrid Compose override with pinned CPU PyTorch and BERT dependencies. No CUDA GPU is required for local inference. `/health` is liveness, `/ready` returns 503 without a loaded model or enabled disconnected worker. Invalid artifacts prevent startup. No public inference endpoint is exposed.

`DetectionService.handle` consumes a canonical request dictionary and returns the shared completion envelope. Missing model produces UNAVAILABLE/unknown. Wrong module/schema/missing URL is rejected. The Kafka worker validates keys, persists in Mongo before publication, replays the same event ID, rejects conflicting retries and commits offsets only after publication. Real Kafka/Mongo and authenticated Gateway/scan verification reports are in model research files.

Follow `docs/phishing/contracts.md` for planned durable result/publication/offset ordering, MongoDB ownership and Gateway access. Preserve existing image/scam behavior when adding phishing subscription and modality mapping.

Optional collector observations use PHISHING_COLLECTOR_URL and PHISHING_COLLECTOR_TOKEN. They remain separate from scoring; the lexical model was not trained on historical metadata. Run the collector separately from internal networks with compose.collector.yml. Address pinning, private-address rejection, verified TLS hostnames, bounded redirects/body sizes, bounded DNS and a process deadline are implemented. Current domain age must never masquerade as age at dataset acquisition.

S3/MinIO: publish a checked local manifest with `python -m services.phishing_url.app.services.artifact_store MANIFEST s3://BUCKET/VERSION`. Use standard boto3 credentials and optional PHISHING_S3_ENDPOINT. Runtime download requires PHISHING_MODEL_S3_URI and trusted PHISHING_MANIFEST_SHA256; PHISHING_MODEL_CACHE must be writable (use /tmp/models in read-only containers). Direct read-only mounts remain supported.
