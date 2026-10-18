# Targeted retraining experiment

The `research_v8` experiment uses the frozen `targeted_20261018_v2` development splits. It does not change the active modern-v5 bundle or the scam/image modules.

## Training and selection

- Fit a new structural LightGBM on all 516,006 training URLs. Give the 209 new targeted training examples a fixed weight of 20; historical rows retain weight 1. This is a bounded research choice, not a label-confidence estimate.
- Preserve the existing domain-masked text branch. Do not add a hostname allowlist or a separate rule for familiar sites.
- Divide calibration domains deterministically between fusion fitting and isotonic calibration. Compare two seven-input fusion models (7 or 15 leaves) on validation only.
- Select the threshold with maximum validation recall subject to a 0.75% false-positive budget, respecting tied scores. Select the candidate with lowest validation FNR, then FPR.
- Freeze artifacts, hashes and threshold before scoring historical regression and familiar-homepage checks.

Independent-test URLs are never loaded by this command. Eligibility for a later independent evaluation requires no familiar-homepage alerts, lower historical FPR and FNR, and no error-rate regression on the small reference set. Passing these development checks is not production acceptance. The independent test still requires a separately frozen acceptance protocol and uncertainty analysis.

```powershell
.\.phishing-test-venv\Scripts\python.exe scripts\train-targeted-phishing.py
```

The command refuses to overwrite an existing experiment. Artifacts remain in ignored `models/phishing_url/checkpoints/research_v8`; the reviewable aggregate report is `models/phishing_url/research/targeted_training_20261018.json`. It never updates the service configuration or copies artifacts into the active bundle.

Provider/reference labels remain imperfect. A URL-only model cannot establish whether an apparently ordinary destination currently hosts a malicious page; live forensic checks remain necessary. Fresh-cohort and familiar-homepage results must be inspected alongside aggregate historical metrics before any promotion.

## First completed result: structural candidate rejected

On the 120,560-row historical regression set, v8 reduced FPR from 0.964% to 0.332%, but increased FNR from 29.230% to 40.846%. Familiar-homepage checks passed. On the 79 new targeted validation URLs (62 references, 17 provider positives), false positives fell from 20 to 10 while false negatives increased from six to seven. These are development diagnostics, not independent estimates of live performance. The candidate was not promoted and the independent test remains unopened.

The results show why lowering false positives alone is insufficient. Aggregate ranking changed little (ROC-AUC 0.96048 to 0.96069), and the selected conservative threshold sacrificed phishing recall. The next complementary experiment uses a sampled, class-balanced URL-text training cohort plus all targeted training examples; targeted rows receive weight 20 in text training and fusion fitting. Isotonic calibration remains unweighted. This architecture preserves the masked branch but adds unmasked character patterns, so the same familiar-homepage gates are essential to catch hostname bias. It is isolated under `research_v9`:

```powershell
.\.phishing-test-venv\Scripts\python.exe scripts\train-targeted-phishing-text.py
```

Its two fusion candidates are selected using validation only at the same 0.75% FPR budget. A targeted-validation non-regression gate and convergence gate supplement the historical/reference/homepage gates. No candidate can deploy itself.

## Complementary result: improved benchmark, rejected deployment

The text model trained on 160,158 sampled/targeted URLs, including all 209 targeted training rows. Both fits converged. Validation selected the 15-leaf fusion and threshold 0.8540587871372558 before regression scoring.

| Historical regression metric (120,560 URLs) | Active v5 | Targeted v9 |
| --- | ---: | ---: |
| Accuracy | 91.608% | 92.722% |
| False-positive rate | 0.964% | 0.566% |
| False-negative rate | 29.230% | 26.108% |
| Phishing recall | 70.770% | 73.892% |
| F1 | 0.8159 | 0.8422 |
| ROC-AUC | 0.9605 | 0.9719 |

These improvements did not satisfy acceptance. Three unique familiar homepages—Google, GitHub and PayPal—were falsely flagged. On the targeted validation cohort, false positives improved from 20/62 to 8/62, but false negatives worsened from 6/17 to 7/17. With only 17 positives, one example changes FNR by 5.88 percentage points; these findings identify failures rather than establish precise population estimates. On the separate 74-row regression reference cohort, false positives improved from 14/72 to 6/72 and misses from 2/2 to 1/2; two positives cannot substantiate general recall.

The unmasked branch continues to introduce hostname-related false alerts despite bounded new-example weighting. No homepage allowlist, domain-specific score override or post-regression threshold adjustment was added. Both candidates remain research artifacts; the active model and independent test are unchanged. Reports: `targeted_training_20261018.json`, `targeted_cohort_20261018.json`, and `targeted_text_training_20261018.json` under `models/phishing_url/research`.

The next data revision needs substantially more independently reviewed benign roots, authentication/payment paths and recent positive roots/landing pages across new domains, with campaign-aware sampling and domain caps. Keep this new independent test sealed while using development data to compare an identity-neutral text representation and source-balanced training. More repeats of existing source patterns or a threshold change alone will not resolve the observed gap. Any improved URL model must also pass the complete live forensic/report/deployment checks before activation.
