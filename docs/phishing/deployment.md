# Current local deployment: dynamic CPU phishing module

Run `.\scripts\start-phishing-infrastructure.ps1` for the default `modern-v5` worker and authenticated live collector. The script creates/reuses an ignored local collector token, enables collection by default and uses `compose.modern.yml` plus `compose.forensics.yml`. Model artifacts are in `models/phishing_url/checkpoints/modern_v5/`; no CUDA is required. Collector cache/quota state lives in the named `phishing_reputation_cache` volume. The older GPU package describes the preserved v1 research model, not the current default.

Use `-Offline` only when live collection is intentionally disabled. Optional `PHISHSTATS_API_KEY` may be set before startup; anonymous provider usage is limited and unknown is never treated as clean. See [dynamic forensic documentation](forensics.md).

Verify readiness at `http://127.0.0.1:8007/ready`. Run `scripts/test-phishing-dynamic.py` with the project test dependencies for the fixed dated mixed sample; `--paths` tests supplemental legitimate page paths. These scripts start isolated authenticated test servers and use real Kafka/Mongo; they do not alter the user's image/scam detector code or use the production relational database. Historical scan IDs are immutable; rescan after updating.

The remaining deployment acceptance criteria (production infrastructure, external provider authorisation, egress/security review and rollback validation) are recorded in `track.md`. Older commands below describe previous research milestones and are superseded by this default.

# Phishing deployment and rollback

The trained LightGBM+BERT hybrid is the default local configuration. The RF lexical bundle is retained for rollback. Every result records detector/model/preprocessing versions, partial coverage and confidence availability. Runtime loads artifacts once and never reads a training dataset.

Local host service: `./scripts/start-phishing.ps1 -Kafka`. This defaults to checkpoints/hybrid/manifest.json, Kafka localhost:9094 and MongoDB localhost:27017. The local environment needs the BERT dependencies. Set PHISHING_MONGODB_URI and KAFKA_BOOTSTRAP_SERVERS for another deployment. The existing Gateway and Scan Management must be running to accept browser scans.

`./scripts/start-phishing-infrastructure.ps1` (also used by the existing development launchers) now selects the trained hybrid Compose override. For rollback use `./scripts/start-phishing-infrastructure.ps1 -Baseline`; this recreates only the phishing worker with the retained RF bundle. Never run both workers on port 8007.

Compose:

```powershell
docker compose -f docker-compose.yml -f services/phishing_url/compose.phishing.yml -f services/phishing_url/compose.hybrid.yml up -d --build phishing
```

The hybrid override installs CPU inference dependencies and mounts the full checked bundle. A CUDA GPU is not required locally; measure actual p50/p95 before scaling. The collector is optional and separately deployed via compose.collector.yml; require its token and do not attach it to trustnet_net. Model scoring does not currently consume current metadata; observations cannot be passed off as historical training features.

Internal `/health` checks process liveness. `/ready` requires a verified artifact and, when Kafka is enabled, connected worker infrastructure. Mongo result persistence precedes Kafka publication, which precedes manual offset commit. Replays reuse the persisted event; conflicting payloads are dead-lettered. Monitor readiness, worker reconnect logs, consumer lag, DLQ growth and result status counts. Raw URLs and secrets are not logged by the worker.

Keep approved model bundles immutable/versioned. Roll back by pointing PHISHING_MODEL_MANIFEST and the read-only mount to the previous bundle and recreating only the phishing service. Replay with the original scan ID returns its original durable result; use a new scan ID for a deliberately re-evaluated model result. Do not delete Mongo ledgers to manufacture a rerun. Kafka/database write and publication are not atomic; durable replay closes the recovery gap.

Verified local Kafka/Mongo replay evidence is in models/phishing_url/research/live_worker_verification.json. That test does not establish authenticated browser end-to-end acceptance or Docker image portability. Baseline source/generalization limitations remain in the model card.

Kubernetes scaling uses more worker replicas with the same consumer group and at least one Kafka partition per desired active worker. The default local topic has one partition, so extra replicas alone do not increase throughput. Keep inference sequential per worker unless offset handling is redesigned. Use read-only artifact volumes, non-root security context, readiness probes and separate collector network policy denying all cluster/service/private destinations.
