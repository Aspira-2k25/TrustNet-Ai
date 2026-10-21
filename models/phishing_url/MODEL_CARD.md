# Selected phishing model: regional-recall-v1

## Deployment identity

The installed components were inspected during integration: both URL-text pipelines use `SGDClassifier`, the structural expert is `LGBMClassifier`, fusion components use `HistGradientBoostingClassifier`, and calibration components use `IsotonicRegression`. These are runtime model identities, not new training results.

The selected teammate package contains eight checksummed components: URL-text and structural models, base fusion/calibration, complementary text/fusion, correction fusion/calibration. URL shape routes to base or correction experts; a bounded second-expert rescue preserves existing primary alerts. This selected release is not the historical BERT/LightGBM `hybrid-v1` release. Do not attribute earlier BERT scores to this checkpoint.

Manifest SHA-256: `30407968c6d02ab076db933a74201d7ac29853637e2d98d2a0faed897a8c6a9c`.

Root/query threshold: 0.7. Path correction threshold: 0.8292682926829269. Secondary rescue thresholds are 0.9936734693877551 for root and 0.9 for query; no path rescue. These belong to this artifact's declared routing policy, not to the message classifier or a universal safety threshold. Runtime also applies local link-forensic policy; the resulting risk index is not a calibrated probability.

## Imported selected-release evidence

Source: `models/phishing_url/research/recall_independent_20261018.json`; training was not repeated during integration.

| Metric | Prior regional baseline | Selected recall candidate |
| --- | ---: | ---: |
| Accuracy | 90.10% | 90.73% |
| Precision | 92.81% | 92.91% |
| Recall | 86.00% | 87.33% |
| F1 | 89.27% | 90.03% |
| False-positive rate | 6.13% | 6.13% |
| TN / FP / FN / TP | 153 / 10 / 21 / 129 | 153 / 10 / 19 / 131 |

The test has 313 rows: 163 benign references and 150 reported phishing URLs. It is a small convenience test with uncertain source labels, only 13 novel benign query references across five domains and no temporal/campaign independence guarantee. It has now been consumed for comparison. The promotion record reports acceptance; this is a modest observed improvement, not population certification. Conditional-routing and final forensic/fusion calibration are not established.

Earlier historical hybrid/test reports remain selected evidence for that earlier model only. Experiment dumps and dated development logs were moved to a recoverable external archive; they are not runtime inputs. Source/licensing records remain in `models/phishing_url/configs/` and `data/dataset_manifest.json`. Check source terms before redistributing datasets or publishing derived artifacts; no new blanket data licence is asserted here.

## Input, safety and explainability

Web URLs use local text and structural features. Other link schemes receive limited offline checks and no website-model score. Evidence includes literal URL structure, navigation parameters and lookalike findings. Absence of a finding does not verify ownership or safety. An isolated optional collector can record public DNS/TLS/static HTTP and reputation observations for standalone scans; it does not train the URL model on current observations.

Install and verify through [the root setup guide](../../README.md). Models are distributed separately from Git and must pass the pinned manifest/component hashes before joblib loading.


## Offline source diagnostic, 21 October 2026

The unchanged selected model was checked through its running inference API on 300 OpenPhish feed URLs and 300 Tranco root-domain references. It flagged 263/300 feed-labelled URLs and 9/300 references: recall 87.67%, precision 96.69%, F1 including abstentions 91.96%, and uncertain share 12.67%. Selective accuracy among decided examples was 95.80%; this excludes uncertain outputs. There were zero service errors. Request p50/p95 were 0.312/0.829 seconds under concurrent developer CPU load.

This is a diagnostic, not a verified-benign or field-accuracy benchmark. Tranco is a popularity ranking, so the 3% reference warning rate is not certified real-world FPR. Full phishing URLs versus reference root domains create a URL-shape confound. The 300 phishing URLs span 282 distinct hostnames; campaign correlation and unknown training overlap remain. These results cannot be compared directly with the earlier 313-row test as a before/after improvement. No weights or thresholds changed, and evaluated destinations were never opened; DNS, TLS, HTML and JavaScript inspection were not measured by this offline run.

Source data and complete outputs remain external. OpenPhish personal/academic research terms and raw-data redistribution restrictions apply: https://openphish.com/terms.html. Tranco provider attribution and licences: https://tranco-list.eu/. Compact aggregate evidence is retained in the existing reference-evaluation JSON, without raw feed URLs.

## PhiUSIIL source-labelled audit and policy correction

Prasad and Chandra's 2024 [UCI PhiUSIIL dataset](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset) is CC BY 4.0. Its official label is 1=legitimate and 0=phishing. A frozen 300/300 sample uses one SHA-selected URL per hostname and removes conflicting hostname labels. Source archive and manifest checksums are retained externally. No destination was opened. Historical labels were not independently re-adjudicated, and registered-domain/campaign correlation or upstream training overlap is not excluded.

The audit proved a separate policy bypass: a 0.95 selected-model reading was changed to 0.15 by an unsubscribe-path override. Popularity and academic/government suffixes could also erase model warnings. Those unmeasured overrides were removed without fitting new weights or changing learned thresholds. A regression check now preserves the original model reading for all these cases.

| Same 600 source-labelled records | Before policy correction | After |
| --- | ---: | ---: |
| TP / FP / FN | 185 / 2 / 115 | 195 / 2 / 105 |
| Recall | 61.67% | 65.00% |
| Precision | 98.93% | 98.98% |
| F1 | 75.98% | 78.47% |
| FPR | 0.67% | 0.67% |
| FPR 95% Wilson interval | 0.18–2.40% | 0.18–2.40% |
| Detector review/uncertain share | 16.00% | 16.50% |

This set was consumed for the before/after correction, not an untouched independent certification. These figures measure available offline detector warnings. Missing website checks can force an incomplete public headline; do not substitute detector recall for full UI recall. The remaining 105 missed source-labelled phishing URLs show a material recall limitation. The point FPR is below 2%, but its confidence interval does not certify a population bound below 2%. CPU request p50/p95 were 0.016/0.032 seconds after correction on this machine; load conditions differed, so no controlled speedup is claimed.
