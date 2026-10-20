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

Install and verify through [docs/TEAM_SETUP.md](../../docs/TEAM_SETUP.md). Models are distributed separately from Git and must pass the pinned manifest/component hashes before joblib loading.
