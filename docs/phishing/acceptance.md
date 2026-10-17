# Acceptance evidence and open gates

## Verified

- 15 October 2026: full three-epoch BERT run, fusion/calibration and frozen test evaluation completed. Hybrid artifact/data checksums verified, local inference passed and CPU Docker worker deployed. Authenticated Gateway/Kafka/Mongo smoke confirmed hybrid-v1 and both branches applied; readiness passed. Frontend build passed; 85 regression tests plus 12 subtests passed across phishing/integration and trust suites. Research/production gates below still apply.

- Branch nirmala; all implementation changes scoped to phishing and its additive integration points. Existing scam-message edits preserved; image detection source untouched.
- Primary version 1 downloaded, metadata labels/license verified, raw/member/prepared/PSL hashes recorded; 500,085 retained rows and domain-disjoint test/development partitions.
- Separate UCI LR/RF experiment with deduplication/conflict exclusion, ten-fold development metrics and frozen test; target interpretation remains conditional on explicit research-supported mapping.
- Full primary lexical LR/RF training/evaluation and LightGBM training; validation/threshold/test roles documented.
- BERT safetensors source loads and supports a real classification forward/backward step. Full GPU fine-tuning not executed locally.
- Fusion/calibration/fallback/bundle/evaluation pipelines implemented. Calibration/threshold partitions isolated from branch checkpoint selection.
- Real Kafka/Mongo request/result/replay test; same persisted completion/event ID on duplicate delivery.
- Deployed non-root baseline Docker image built, health/readiness pass with Kafka/Mongo connected.
- Real signed JWT Gateway → scan dispatch → deployed detector → persisted scan/trust report succeeds; missing auth/invalid scheme rejected and another signed user denied. Relational store for this smoke was an isolated SQLite database, not PostgreSQL deployment verification.
- Phishing UI uses Gateway submission/polling, real scan IDs and explicit errors; dedicated phishing report/PDF avoids image verdicts. Production frontend build passed.
- 82 regression tests plus 12 subtests passed before additional storage tests; three new storage/completion tests passed. Final post-change suite recorded in track.md.

## Required before claiming the entire plan done

- Resolve the live HTTPS reliability gap found by the varied URL suite. Source training has zero legitimate HTTPS examples and only six phishing HTTPS examples; the source test is almost entirely HTTP. HTTPS confidence is now withheld and risk is explicitly experimental. Acquire representative labelled data and retrain/revalidate before a production reliability claim.

- Full GPU run and component/hybrid test comparison are complete; local promotion passed. Still measure production latency distributions and robustness before a production release. Hybrid improves F1/false-positive rate while BERT alone improves recall/AUC at their validation-selected operating points.
- Run primary ten-fold component training and report spread; prepared ten folds alone are not ten trained models. Current primary baselines use the fixed initial train/validation/test split.
- Resolve authoritative UCI target dictionary and conflicting published target conventions before treating its phishing precision/recall as definitive.
- Acquire licensed freshness phishing + independently labeled legitimate snapshots; remove overlapping training domains and measure source/temporal shift. Feed absence or Tranco rank alone cannot label a URL legitimate.
- Establish historical collection parity and train/evaluate an enriched metadata configuration. Current lexical artifacts do not use WHOIS/TLS/DNS/HTML observations as learned features.
- Complete full BGL paper review and method comparison; GNN remains a later upgrade.
- Verify PostgreSQL production configuration, MinIO publication/download, hybrid Docker deployment, rollback and Kubernetes rollout in their target environments. Code/configuration alone does not establish these operational gates.
- Run bounded robustness slices, domain-bootstrap confidence intervals and production throughput monitoring on the promoted bundle.

Do not report these gates complete merely because a runnable pipeline or reference deployment exists.
