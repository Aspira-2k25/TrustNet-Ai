# Phishing service foundations

**Current selected runtime:** `regional-recall-v1`. Use [docs/TEAM_SETUP.md](../../docs/TEAM_SETUP.md) and `scripts/setup/install-phishing.ps1`; this runtime is isolated in `.venv-phishing` and does not use the image environment. The internal `/infer` endpoint performs bounded offline URL-model/link analysis for message fusion and standalone local fallback. The Kafka worker additionally supports the isolated optional live collector. The older baseline/training commands below are reference material, not the selected startup command. Current model identities and evaluation limitations are in `docs/phishing/model_card.md`.

Install and launch the selected runtime from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts/setup/install-phishing.ps1
.\start-dev.bat
```

`requirements-runtime.txt` is the isolated selected service runtime. `requirements.lock` belongs to the historical research environment. The launcher selects `compose.modern.yml` with `regional_recall_v1`; BERT, GPU training and external datasets are not required for this release. `/health` is liveness, while `/ready` requires the model and, when enabled, its broker connection. Invalid artifacts prevent startup. Browser requests use the authenticated Gateway, not the internal inference endpoint.

`DetectionService.handle` consumes a canonical request dictionary and returns the shared completion envelope. Missing model produces UNAVAILABLE/unknown. Wrong module/schema/missing URL is rejected. The Kafka worker validates keys, persists in Mongo before publication, replays the same event ID, rejects conflicting retries and commits offsets only after publication. Real Kafka/Mongo and authenticated Gateway/scan verification reports are in model research files.

See [contracts](../../docs/phishing/contracts.md) for worker ordering and ownership, and [model card](../../docs/phishing/model_card.md) for measured results and limitations. Run `.\.venv\Scripts\python.exe scripts/checks/verify-integration.py --kafka` for isolated authenticated scan, real worker completion, saved history and owner isolation checks.

Optional collector observations use PHISHING_COLLECTOR_URL and PHISHING_COLLECTOR_TOKEN. They remain separate from scoring; the lexical model was not trained on historical metadata. Run the collector separately from internal networks with compose.collector.yml. Address pinning, private-address rejection, verified TLS hostnames, bounded redirects/body sizes, bounded DNS and a process deadline are implemented. Current domain age must never masquerade as age at dataset acquisition.

S3/MinIO: publish a checked local manifest with `python -m services.phishing_url.app.services.artifact_store MANIFEST s3://BUCKET/VERSION`. Use standard boto3 credentials and optional PHISHING_S3_ENDPOINT. Runtime download requires PHISHING_MODEL_S3_URI and trusted PHISHING_MANIFEST_SHA256; PHISHING_MODEL_CACHE must be writable (use /tmp/models in read-only containers). Direct read-only mounts remain supported.
