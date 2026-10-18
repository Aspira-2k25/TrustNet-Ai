# Phishing performance improvement experiment

## Scope and safeguards

This experiment changes only phishing research tooling and data. The active modern-v5 model, evidence weights, reports, image/scam implementations and shared infrastructure are not modified by the training script. Candidate artifacts live separately under `checkpoints/research_v6`.

The current URL-only operating point has high precision but low recall, particularly on the PhiUSIIL slice. Its historical test has already influenced previous development and is explicitly a regression benchmark, not an untouched acceptance test. UCI's official dictionary confirms PhiUSIIL label 1 = legitimate, 0 = phishing; the training code correctly maps these to internal 0 = legitimate, 1 = phishing.

## Fresh local research challenge

`scripts/collect-phishing-research-holdout.py` freezes current provider-reported positives and reference negatives extracted from same-host links on official public pages. It never opens reported phishing URLs. The initial snapshot recorded an intentionally blocked cross-host feed redirect and was retained as an incomplete collection record. The v2 collection uses the provider's verified GitHub feed endpoint and contains both classes.

The collection is not a production blacklist. OpenPhish terms restrict the feed to permitted noncommercial research and prohibit redistribution; feed contents and URL-level results remain under ignored `models/phishing_url/data/`. Only aggregate findings are suitable for a shareable research summary. Sources: https://openphish.com/terms.html and https://github.com/openphish/public_feed.

Official-page reference links are not independently certified nonphishing. Provider positives are not independently adjudicated. A single feed can contain campaign clusters, and collection time is not attack creation time. The convenience challenge therefore provides limited prospective evidence, not deployment-wide accuracy. A domain-disjoint subset relative to legacy fitting domains is reported separately. All fresh domains are removed from candidate training, calibration and threshold selection.

## Fixed candidate protocol

1. Reconstruct the original source/domain partitions and quarantine conflicting URL labels. Preserve original sources and hashes.
2. Verify zero domain overlap and reserve all fresh challenge domains before fitting.
3. Fit a source/class-balanced LightGBM structural candidate with early stopping on a separate subset of training domains.
4. Fit a source/class-balanced masked character TF-IDF/SGD text candidate with a 200-iteration limit; record convergence warnings.
5. Fit fusion with branch probabilities plus all 30 structural inputs on one calibration-domain partition; fit isotonic calibration on the other.
6. Compare retuned-v5, balanced structural and balanced-fusion candidates on validation data only. Choose maximum recall subject to a 1% false-positive budget. Identical scores cannot be split to make the budget appear satisfied.
7. Freeze candidate choice and threshold before evaluating historical regression and the frozen fresh challenge. Save predictions, error slices and counts; do not silently tune on those results.
8. Reject promotion unless both FPR and FNR improve on both evaluations. Eligibility is not activation: integration, loader checks, policy checks and regression tests remain necessary.

Run from the repository root using the isolated phishing environment:

```powershell
.\.phishing-test-venv\Scripts\python.exe scripts\collect-phishing-research-holdout.py
.\.phishing-test-venv\Scripts\python.exe scripts\improve-phishing-model.py
.\.phishing-test-venv\Scripts\python.exe -m unittest models.phishing_url.tests.test_research_improvement -v
```

The frozen collection and completed experiment intentionally refuse overwriting. New experiments need a new data/artifact version and another genuinely independent acceptance set. No GPU is required. Aggregate results are written to `models/phishing_url/research/improvement_20261018.json`; URL-level errors stay in ignored data.

## First completed result

The newly balanced structural and fusion candidates did not outperform retuned-v5 on validation recall at the fixed 1% FPR cap. The selected retuned-v5 operating point raised the threshold from 0.70 to approximately 0.8611. On the historical regression set, FPR fell from 0.964% to 0.530%, but FNR rose from 29.150% to 35.022%. On the 807-row reference challenge, FPR fell from 5.523% to 4.339%, but FNR rose from 44.333% to 50.667%. It was rejected and never activated.

The stricter subset excludes all domains seen by legacy fitting and all previously recorded URLs: 709 rows (413 reference negatives and 296 provider positives). Baseline FPR is 5.327% and FNR 44.595% on this subset. These are convenience-sample diagnostics, not general deployment rates.

Error slices expose concrete priorities. Historical root-path URLs account for 6,200 of 9,263 false negatives. Legitimate URLs with credential terms number only 22 in the historical test, and 17 are flagged; this tiny slice indicates inadequate hard-negative coverage but cannot establish a general population FPR. The recent provider challenge has a different error pattern: 89 of 96 reported-positive long-path URLs are missed by the baseline, reinforcing distribution-shift concerns. No source label is changed merely because a model disagrees.

## Second predefined architecture experiment

`scripts/train-phishing-complementary.py` retains the existing structural and masked-text branches and adds a regularized hostname-text branch. It fits HGB fusion on all structural inputs and the three branch outputs, then isotonic calibration on separate calibration domains. Threshold selection is validation-only under a 0.75% FPR cap. Registered domain names are learned text rather than per-domain verdict exceptions; all domain separation and reserved challenge exclusions remain in force.

Because the challenge has now been evaluated, the second experiment explicitly calls it a reused regression challenge rather than a pristine acceptance set. Any positive result requires additional independent validation and familiar-homepage regression checks before activation. No candidate automatically modifies the active runtime.

## Completed complementary experiment: improvement on source, rejected for activation

The complementary classifier converged in 31 iterations without a convergence warning. Validation selected threshold 0.8667728022 under the predeclared 0.75% FPR cap. The threshold was not chosen using regression or challenge labels.

| Historical regression metric (120,664 URLs) | Active v5 | Research v7 |
|---|---:|---:|
| Accuracy | 91.613% | 92.712% |
| Precision | 96.333% | 97.748% |
| Recall | 70.850% | 74.032% |
| F1 | 81.649% | 84.253% |
| ROC-AUC | 0.9606 | 0.9708 |
| FPR | 0.964% | 0.610% |
| FNR | 29.150% | 25.968% |
| False positives | 857 | 542 |
| False negatives | 9,263 | 8,252 |

These are descriptive regression improvements, not an independent performance guarantee. Historical probability ECE worsened from approximately 0.00593 to 0.01162 despite improved Brier score; better classification alone is not proof of better confidence calibration.

On the recent 807-row convenience challenge, false positives decreased from 28 to 26, but false negatives remained 133/300. No recall improvement was established. More importantly, the fixed 19-homepage regression exposed three new false phishing alerts: Google, GitHub and PayPal. The character-lookalike example is an illustrative forensic test and is not counted as an independently labeled phishing example.

**Decision: do not activate research-v7.** Both the lack of challenge recall improvement and the familiar-homepage regressions prevent promotion. No domain-specific exceptions were added to conceal these failures. Active modern-v5 artifact hashes remain unchanged.

Evidence: `models/phishing_url/research/improvement_20261018.json`, `complementary_20261018.json`, and `complementary_homepages_20261018.json`.

## Work remaining before a deployable improvement

- Collect a larger, independently labeled development corpus of legitimate authentication/account/payment URLs, difficult benign long paths, recent provider-confirmed phishing on ordinary-looking domains, and shared-hosting campaigns. The current official-page collection is an evaluation reference set, not a sufficiently varied replacement training corpus.
- Keep a separate future source/domain/campaign-aware acceptance set. The present challenge is now development evidence and cannot be reused as proof of independent acceptance.
- Investigate regularized domain representations without restoring hostname-identity bias; keep all familiar-homepage and hard-negative checks.
- Validate model-plus-live-forensics decisions separately, recording unavailable checks and review/abstention rates. Do not count blacklist matches on a feed-derived benchmark as independent learned-model accuracy.
- Recheck calibration, complete runtime integration/rollback tests and run latency/resource measurements before switching the active bundle. No production-wide FPR/FNR claim is justified yet.
