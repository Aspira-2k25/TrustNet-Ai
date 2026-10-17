# Phishing model card — current CPU model and historical experiments

## Current deployment: modern-v5 / dynamic-v2 (16 October 2026)

The CPU ensemble replaces the v1 BERT default. Registered-domain identity is masked in its URL-text branch; structural features and subdomain/path/query/fragment patterns are learned without per-domain verdict exceptions. Live DNS/TLS/page/form/RDAP/reputation collection is enabled by normal phishing startup. The previous blanket HTTPS rejection, named-brand rules and fixed 75-point output are superseded. See [audit](audit-2026-10-16.md) and [dynamic policy](forensics.md).

The structural component used 516,945 training URLs from the approved primary corpus plus official UCI PhiUSIIL (Prasad and Chandra, 2024, CC BY 4.0). The masked text component used a deterministic 200,000-row training subsample. There are 53,041 calibration rows, partitioned by domain into 28,422 for fusion fitting and 24,619 for probability calibration; 42,146 validation rows select the alert threshold (0.70), and 120,664 rows form the source test. No domain overlaps between these partitions. Training includes 94,316 legitimate and 34,185 phishing HTTPS examples; scheme is not a learned feature.

| Source test metric | modern-v5 |
|---|---:|
| Precision | 0.9633 |
| Recall | 0.7085 |
| F1 | 0.8165 |
| ROC-AUC | 0.9606 |
| False-positive rate | 0.00964 |
| False-negative rate | 0.2915 |

These metrics are for the URL model, not the full live evidence policy. Development reused the evaluation partition after rejecting other candidates; they are not a pristine deployment benchmark. All 19 held-out official homepage challenges remained below the phishing alert threshold; some received a review-level score. Challenge names are evaluation exclusions, not runtime allowlists. The SGD text component reached its 25-iteration cap and emitted a convergence warning. The release is a local prototype, not production certification.

The combined risk index supplements model output with generic observed forensic findings and fresh exact reputation reports, using disclosed policy weights. It is not empirically calibrated as a probability. The source model alone misses about 29% of labelled phishing examples at this operating point; current reputation/page evidence is complementary rather than proof that those misses disappear generally.

A structure-only candidate (F1 0.6923, recall 0.5501) and an unmasked text ensemble (F1 0.8763, recall 0.8123, but 5/19 homepage false alerts including Google/GitHub) were rejected as standalone replacements. Their metric reports remain for audit. The unused unmasked-v4 trainer/runtime branch and its binary artifacts were removed in the 17 October cleanup; the structural bundle remains a dependency of current retraining. Current evidence is `masked_candidate.json`, `masked_candidate_promotion.json`, `dynamic_url_audit.json` and the dated audit document.

## Historical experiments and superseded policies


## Historical forensic policy, 16 October 2026

The current policy is `forensics-v1`; it supersedes the branch-only and confidence-only safeguards described below. Offline forensic rules run for every valid URL, including model-unavailable cases. An optional isolated collector supplies registration, DNS, TLS, redirect and password-form observations. Unsupported v1 HTTPS probabilities are now withheld entirely. Model disagreement, uncorroborated positives and forensic review indicators also abstain. Strong forensic findings use an explicitly uncalibrated ordinal severity index (75/100, native anomaly score), **not a phishing probability**. Rule evidence and model diagnostics remain separate. See [forensic policy](forensics.md) for exact rules, limitations, activation and score semantics. This is a safety/interpretability correction, not a measured improvement in general model accuracy.

Empty root paths are normalised to `/` at inference; fragments, encoded paths and the submitted URL are preserved. Original training metrics below apply to frozen source preprocessing, not the new combined policy. Independent evaluation remains required.

## Historical assessment safeguard — branch agreement

An additional CPU URL-text candidate was trained on the primary corpus plus URL/label fields from official UCI PhiUSIIL (Prasad & Chandra, 2024, CC BY 4.0; https://archive.ics.uci.edu/dataset/967/phiusil-phishing-url-dataset). It uses scheme-neutral character TF-IDF and calibrated linear classification, with 495,227 training / 104,429 validation / 133,140 test rows, zero domain overlap and challenge domains excluded from training/calibration. **It was not promoted**: test F1 0.8178, recall 0.6985, and a high false-positive score on the GitHub challenge fail the intended release criteria. This experiment is evidence of attempted remediation, not a claim that general accuracy is fixed. Artifacts remain separate in checkpoints/url_text_v2; evidence is accuracy_candidate.json and accuracy_candidate_promotion.json.

Earlier scans used `branch-agreement-v1`. Each branch's existing calibrated, validation-selected fallback threshold defined its decision. Disagreement returned UNCERTAIN/UNAVAILABLE with `MODEL_DISAGREEMENT`, no prediction confidence, and no fused trust score. Google and Wikipedia triggered that safeguard in live end-to-end tests, but branch agreement alone did not cover all false positives. The current policy is described above.

On the reused 10,416-row threshold-validation partition, 8,793 rows (84.4%) remain assessed; 1,623 are uncertain. Of the original 116 false-positive alerts, 99 are now withheld. These are selective validation diagnostics, not a new independent accuracy measurement or a claim that abstained cases are safe. The source-test metrics below describe the original raw hybrid, before this assessment safeguard.

Reports now display the shared trust-engine risk score (higher means more risk), normal-language observed/model-feature reasons, analysis layers and PDF sections. Historic hybrid reports without the new policy marker require a rescan; their old scores are withheld in the phishing report/history UI.

## Live URL smoke finding — HTTPS coverage gap

The varied URL smoke suite flagged familiar public homepage addresses (including Google and Wikipedia) at high risk. These examples have no independently collected labels and are not a new accuracy benchmark, but the results expose a serious deployment reliability concern. The frozen training partition contains 282,538 legitimate HTTP, 77,522 phishing HTTP, six phishing HTTPS and **zero legitimate HTTPS** examples. The test partition has only one HTTPS example, labelled phishing. The high source-test scores therefore do not establish HTTPS generalization.

The earlier confidence-only policy marked HTTPS inputs outside validated coverage while still displaying experimental raw scores. The current forensic policy withholds unsupported numerical model assessments completely. Representative labelled HTTPS data, versioned preprocessing/training and independent calibration/evaluation remain required before claiming reliable live HTTPS detection. Evidence: `scheme_coverage.json`, historical `url_suite.json`, and current `forensics_regression.json` in model research outputs.

## Kaggle hybrid results — 15 October 2026

Full three-epoch BERT training completed on 360,066 frozen training URLs. Imported from the user's Kaggle `results.zip`; eight hybrid artifact hashes and the local prepared dataset hash match the manifest. The selected validation operating point uses 10% LightGBM, 90% BERT, isotonic calibration and threshold 0.53. Test thresholds were not selected on the test set.

| Configuration | Test precision | Test recall | Test F1 | Test ROC-AUC | False positive rate |
|---|---:|---:|---:|---:|---:|
| LightGBM fallback | 0.7688 | 0.5997 | 0.6738 | 0.8787 | 0.0495 |
| BERT fallback | 0.9289 | 0.9417 | 0.9353 | 0.9853 | 0.0198 |
| Calibrated hybrid | 0.9520 | 0.9238 | 0.9377 | 0.9788 | 0.0128 |

The hybrid correctly detected 19,893 phishing URLs, missed 1,640, and flagged 1,003 legitimate URLs among 100,013 held-out rows. BERT alone has better recall, ROC-AUC and Brier score; the hybrid has slightly better F1 and fewer false positives at these validation-selected thresholds. Hybrid Brier score is 0.02342 and ECE 0.00467. Reported inference p50/p95 is 96.11/123.41 ms in the Kaggle evaluation environment, excluding collection; these are not local production latency measurements.

The bundle is deployed locally in the CPU phishing worker. An authenticated Gateway/Kafka/Mongo smoke returned hybrid-v1 with both branches APPLIED, matching scan IDs, a persisted report and owner isolation; readiness passed. The measured first deployed scan took 1,635 ms, which is a single cold observation, not a latency distribution. The smoke uses isolated SQLite for the relational scan store. Robustness/freshness tests, ten-fold training and production acceptance remain pending. The baseline sections below record the earlier milestone; references there to pending GPU results are superseded by this section. Evidence: `models/phishing_url/research/hybrid_test.json`, `kaggle_import.json`, `kaggle_training.log`, `hybrid_local_smoke.json` and `platform_verification.json`.

## Inputs and output

Absolute HTTP(S) URL. The baseline has fourteen lexical features; it does not inspect live HTML, verify certificates, query reputation feeds or establish credential theft. Positive class 1 means phishing; native_score estimates phishing probability. risk_score is round(100*p). Labels use a validation-selected threshold. Scores are uncalibrated for LR/RF; baseline confidence is explicitly unavailable (0). Evidence is observed URL facts, not proof. Hybrid code uses calibrated weighted voting, native TreeSHAP and measured single-branch fallbacks after training.

## Data

Approved Kaggle taruntiwarihp/phishing-site-urls v1: 549,346 rows before cleaning, 500,085 retained. Train 360,066 / validation 40,006 / test 100,013; zero registrable-domain overlap, private suffixes included. Source hashes, license metadata, exclusions and ten development folds are recorded in research/primary_preparation.json. Almost all source URLs omit a scheme, so inferred HTTP is marked in prepared data. Original collection lineage, per-row dates and campaign families are unavailable. No temporal or campaign-level generalization claim is made.

UCI experiments are separate: deduplicated unambiguous pre-extracted feature vectors; 64 conflicting vectors removed; no raw URL/domain/date information. Caller supplied -1=phishing, +1=legitimate; comparative research supports that direction but the supplied official metadata does not define it. Interpret positive-class UCI precision/recall conditionally until the author's target dictionary is obtained. These artifacts are never live URL models.

## Measured results

| Experiment | Test F1 | Test recall | Test ROC-AUC |
|---|---:|---:|---:|
| Primary lexical LR | 0.5321 | 0.3967 | 0.7387 |
| Primary lexical RF | 0.6670 | 0.5743 | 0.8766 |
| UCI LR, conditional mapping | 0.9471 | 0.9391 | 0.9854 |
| UCI RF, conditional mapping | 0.9695 | 0.9679 | 0.9963 |

UCI and primary metrics describe different inputs/splits; they are not interchangeable. RF still misses roughly 43% of held-out phishing at its selected threshold. Do not present high overall accuracy as evidence that all phishing is detected. LightGBM validation metrics and early-stopped iteration are in research/primary_models.json; final hybrid test/ablation/latency results remain pending GPU training. No hybrid improvement claim is made.

## Promotion and limitations

RF is a provisional usable baseline, not the final architecture. The main milestone requires full BERT training on the frozen training rows, validation-only weighted voting, isolated isotonic calibration and threshold selection, frozen test branch/hybrid comparison, robustness slices and freshness evaluation. Report operating-point false positives and misses before promotion. Registration/TLS/HTML observations are optional and not model features in the current artifact. GNN is future work.
