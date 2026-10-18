# Accuracy and recall improvement — 18 October 2026

The new local default is `regional-recall-v1`, packaged under `checkpoints/regional_recall_v1`. This adds a development-selected second-expert rescue policy to regional-v1. Learned component weights are unchanged; this was an ensemble decision-policy improvement, not a BERT retraining run. No CUDA is needed. Image/scam modules and shared detector contracts are unchanged.

## Decision policy

Every original model alert is preserved. Only an original negative can be rescued by the other checked expert. Root URLs require a correction-expert score of at least `0.9936734693877551`; query-bearing URLs require `0.9`. Path-only URLs have no extra rescue rule. Primary expert thresholds remain 0.7 for root/query and 0.8292682926829269 for path-only URLs.

These are model-score boundaries, not confidence percentages. There is no runtime domain allowlist or named-domain score override. Known-site development controls constrain rescue thresholds with a score margin; targeted validation and reference negatives cannot gain false alerts. Thresholds maximize additional validation detections within an extra FPR budget of 0.1 percentage points and must improve accuracy. The selected candidate added zero validation false positives. Its bundle was frozen before independent scoring: manifest SHA-256 `30407968c6d02ab076db933a74201d7ac29853637e2d98d2a0faed897a8c6a9c`.

## New independent test

The earlier 153-URL test remains consumed and was not reused for acceptance. A separate 300-URL reservation excluded all 346,813 known historical/source/evaluation domains and 142,423 known distinctive path signatures. Before any predictions, it was expanded with 13 verified benign query references across five domains, producing v2 with 313 URLs: 163 reference negatives from 35 domains and 150 provider positives from 147 domains. Parent and child CSVs remain immutable; both are now marked consumed through the child evaluation.

Positive labels came from the [OpenPhish community feed](https://openphish.com/phishing_feeds.html); reported phishing pages were never visited. The optional Phishing.Database feed yielded no URL rows. Reference negatives are curated operator pages and observed links fetched with public-address pinning, verified TLS and HTTP 200, not independently certified safe pages. Raw data and evidence remain local/ignored. Source snapshots, hashes and label provenance are preserved.

Both models below were evaluated on this exact same new test:

| Model-only metric | Regional v1 | Regional recall v1 |
| --- | ---: | ---: |
| Accuracy | 90.10% | 90.73% |
| Phishing recall | 86.00% | 87.33% |
| Precision | 92.81% | 92.91% |
| F1 | 89.27% | 90.03% |
| False positives | 10 / 163 | 10 / 163 |
| False negatives | 21 / 150 | 19 / 150 |
| Brier score | 0.07661 | 0.07397 |

The improvement is two additional phishing detections and no additional false alerts on this sample. The earlier 66% recall was measured on a different 153-URL dataset; it is not the baseline for this comparison. The result is a modest observed improvement, not proof of a population-wide gain. Acceptance required higher accuracy and recall, no additional query false positives, no worse Brier score, preservation of primary alerts and an FPR increase below one percentage point. All gates passed, with zero observed FPR increase. There was no test-based retuning.

## Development and historical results

Validation (42,187 URLs): accuracy 90.0775% → 90.6511%, recall 71.31% → 73.14%; 242 additional phishing detections, no additional false alerts. The older 120,560-row regression: accuracy 91.80% → 92.22%, recall 71.34% → 72.95%; 510 additional phishing detections and two additional false positives (805 → 807). Thus unchanged false alerts on the new test must not be generalized to every cohort. Existing reference/homepage controls pass.

## Report and activation

The report records the primary estimate/boundary and whether the second expert triggered the alert. Risk and inverse trust indices retain their existing meaning. No statistical prediction confidence or routed-system probability calibration is claimed. Live forensic policy is unchanged and still supplements the URL model.

Both phishing launchers and `compose.modern.yml` default to `regional_recall_v1`. Previous `regional_v1` and `modern_v5` bundles are preserved. Roll back with `$env:PHISHING_MODERN_BUNDLE='regional_v1'` and run `scripts/start-phishing-infrastructure.ps1`. Submit a new scan to see the new version; saved reports retain their original results.

Deployment verification: 69 Python tests, phishing report tests, TypeScript, targeted lint and the frontend production build passed. The running worker reports ready with version `regional-recall-v1` and manifest SHA-256 `30407968c6d02ab076db933a74201d7ac29853637e2d98d2a0faed897a8c6a9c`. Linux inference and actual live Google/PayPal collection/report checks passed with HTTP 200 and no strong phishing indicators; Google's registration check was unavailable. This does not constitute a new authenticated browser/Gateway/published Kafka-event test. Evidence is in `models/phishing_url/research/recall_deployment_20261018.json`.

Reproduction: `reserve-phishing-recall-test.py`, `extend-phishing-recall-test.py`, `improve-phishing-recall.py`, guarded one-shot `evaluate-phishing-recall.py`, and `promote-phishing-recall.py`. Completed experiments refuse overwrite. The consumed test must not support another fresh acceptance claim. `smoke-phishing-regional.py --bundle regional_recall_v1` checks actual local inference/report behavior, both rescue routes, known legitimate roots, lookalikes and a reputation fixture without visiting phishing pages.

Remaining limitations: only 13 fresh benign query references, provider/reference label uncertainty, source/convenience-sample bias, incomplete campaign/temporal independence, calibration not established, and 19/150 missed positives on the new sample. Python documentation still has an overly high review score. More independently reviewed active/compromised pages, benign authentication/query routes, larger independent tests and full authenticated browser/Gateway/Kafka verification remain necessary.
