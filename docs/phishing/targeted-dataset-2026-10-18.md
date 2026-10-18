# Targeted phishing dataset — 18 October 2026

## Status update — 18 October 2026

The v2 test described below was subsequently consumed once for the frozen regional candidate after all development gates passed. Its comparison report is `models/phishing_url/research/regional_independent_20261018.json`; `sealed_test/consumption.json` prevents another fresh evaluation. Dataset CSVs and their original integrity proofs remain unchanged. Earlier statements that the test is sealed/unscored describe the dataset-build checkpoint, not its current status. New acceptance work requires a new independently reserved test.

## Result and scope

The current dataset revision is `models/phishing_url/data/targeted_20261018_v2`. It contains two-column URL/label exports and separate evidence/lineage. Internal labels are **0 = legitimate reference/source label, 1 = phishing provider/source label**. No model predictions were used as labels. No reported phishing page was visited.

This is a development research corpus and a new domain-independent research test, not a complete inventory of the web or independently certified ground truth. Existing source labels retain their original uncertainty. New negatives are curated operator references supported by observed public links, validated TLS and HTTP 200; TLS alone never creates a legitimate label. Positives come from PhishStats reports with a score of at least 7 and a report date within 120 days. Neither evidence tier is infallible.

## Files and counts

| Split | Legitimate/reference | Phishing/report | Total |
|---|---:|---:|---:|
| `train.csv` | 372,220 | 143,786 | 516,006 |
| `calibration.csv` | 37,234 | 15,827 | 53,061 |
| `validation.csv` | 28,994 | 13,193 | 42,187 |
| `sealed_test/url_labels.csv` | 103 | 50 | 153 |
| `historical_regression.csv` | 88,880 | 31,680 | 120,560 |
| `regression_reference.csv` | 72 | 2 | 74 |

`train.csv`, `calibration.csv` and `validation.csv` retain **610,916 historical development examples** and add **338 new targeted development examples**. Overall there are **565 accepted targeted examples**: 209 training, 50 calibration, 79 validation, 74 previously seen-domain regression references and 153 independent test records. `targeted_train.csv`, `targeted_calibration.csv`, `targeted_validation.csv` and `targeted_regression_reference.csv` expose the small new cohorts separately, also with just URL/label columns.

`provenance.jsonl` records source, evidence tier, timestamps where known, source page, observed destinations/TLS/page hashes for references, provider report information for positives, row ID, domain/group, cohort and slice tags. Test provenance stays separately under `sealed_test/`. Missing historical collection dates remain null; they are not invented.

## Independent test reservation

The 153 test URLs cover **25 legitimate-reference domains and 48 phishing-report domains**. The reservation excludes domains in both original URL-source files, all earlier development/test partitions, and the previously evaluated homepage/fresh challenges. The test contains 26 legitimate authentication/account/payment URLs, 43 legitimate long-path URLs and 23 reported-positive root-path URLs. These tags overlap and do not change labels.

Known new near-duplicate campaign paths are grouped with registered domains before splitting; private hosting suffixes keep independent tenants separate. Generic/root-path campaigns cannot be identified reliably from strings, so complete campaign independence is **not** claimed. Collection/report time is preserved, but the historical sources lack timestamps; this is **not** a proven temporal holdout.

`sealed_test/reservation.json` was written before training exports. `dataset_manifest.json` binds the CSV and provenance hashes. `verification.json` checks those hashes, counts and domain/group separation, including every raw historical URL source. `normalization_label_audit.json` checks canonical-label consistency against both complete original sources. Zero domain/URL overlap and zero normalized source-label conflicts were found. **No model has scored this test.** Sealing is a reproducible protocol and checksum boundary, not encryption or an operating-system access restriction.

The small test meets the predeclared research minimum (50 examples and at least five domains per class); it is not large enough to certify deployment FPR/FNR. Additional adjudication and a larger, more diverse acceptance sample remain desirable.

## Collection and cleaning

- Two curated source configurations cover public authentication, developer, commerce, government, education and finance origins. Only observed official links are considered; unknown paths and modified lookalike domains are never fabricated and labeled.
- Official pages use public-address pinning, verified TLS, operator-scoped redirects, bounded reads and a small concurrency limit. No JavaScript, account login, form submission or user session is used. Failed/blocked/unverified links are retained only for review.
- PhishTank's public download was unavailable in this environment. It contributed no labels. Nine successful paginated PhishStats requests collected 900 report rows. Collection stopped at HTTP 429 on the next page; limits were not bypassed.
- The official batches collected 483 reference rows. Twelve duplicate evidence rows were merged. Domain caps (12 references or five provider positives per domain) prevent repeated pages from dominating the new cohort. This left 565 targeted examples; 806 candidate rows were excluded by diversity/review policy. Exclusion does not mean the provider label was false.
- Existing data were cleaned conservatively: 558 ephemeral-token URLs, 19 credential-bearing authorities and eight overlength URLs were excluded; 12 older entries were replaced by current same-label evidence. Another 25 canonical aliases were deduplicated. Conflicting labels had already been quarantined during source preparation; the additional full-source canonical audit found no label conflicts in the exported dataset.
- The first revision's novel-domain test had only 32 positives, below the 50-positive research minimum. It was not evaluated or used for training. Revision v2 preserves that record, adds the available extra provider batch, and prioritizes meeting the unchanged test minimum before allocating remaining novel groups to development. No prediction outcomes influenced the revision.

## Using the dataset for the next training round

Use only the three development splits for fitting, fusion/calibration and threshold selection. The loader returns only URL and integer label, preventing provenance, collection success or provider identity from becoming accidental classifier features:

```python
from pathlib import Path
from models.phishing_url.datasets.targeted import development_rows

dataset = Path('models/phishing_url/data/targeted_20261018_v2')
training = list(development_rows(dataset, 'train'))
calibration = list(development_rows(dataset, 'calibration'))
validation = list(development_rows(dataset, 'validation'))
```

The loader requires integrity/label verification, checks the split hash, and rejects independent-test or regression splits for fitting. New targeted cohorts should be tracked separately during development; compare bounded reweighting/sampling options using validation data rather than allowing the large historical cohort to overwhelm rare hard negatives. Do not oversample validation/test records or change labels because a model disagrees.

Before any independent-test inference, freeze the candidate artifacts, preprocessing, threshold and promotion criteria. Use older regression/homepage checks first. If those fail, keep the independent test unopened. Once the independent test influences decisions, mark it consumed and reserve a genuinely new test for a later acceptance claim. Nothing in this dataset build changes the deployed modern-v5 bundle.

Forensic observations remain separate. Current evidence collection is asymmetric (positive pages were deliberately not visited); feeding its missingness or TLS/page-success fields into a trained classifier would leak the labeling/collection process. A future learned live-evidence model needs comparably collected positive and negative evidence. Existing bounded live forensics continue to supplement inference independently.

## Reproduction and source terms

```powershell
.\.phishing-test-venv\Scripts\python.exe scripts\collect-targeted-phishing-data.py
.\.phishing-test-venv\Scripts\python.exe scripts\collect-targeted-phishing-data.py --supplement
.\.phishing-test-venv\Scripts\python.exe scripts\extend-targeted-phishing-data.py
.\.phishing-test-venv\Scripts\python.exe scripts\build-targeted-phishing-dataset.py --revision v2
.\.phishing-test-venv\Scripts\python.exe scripts\verify-targeted-phishing-dataset.py --revision v2
.\.phishing-test-venv\Scripts\python.exe -m unittest models.phishing_url.tests.test_targeted_dataset -v
```

Completed snapshots deliberately refuse overwrite. Use a new version to refresh data, not these commands to replace a sealed test. The older source archives and cached preparation are required for reproduction; public endpoints may later change or become unavailable.

Raw URLs and provider evidence remain under ignored data paths. [PhishStats terms](https://phishstats.info/terms) permit lawful research within quotas but restrict raw-feed redistribution without permission. Existing Kaggle source licensing and [UCI PhiUSIIL attribution](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset) still apply. Do not upload the raw combined corpus to GitHub or publish it with a paper without reviewing source permissions. Aggregate summaries and tooling are kept separately for review.

Remaining gaps include more independently reviewed labels, fresh internationalized/lookalike examples, benign shared-hosting content, stronger campaign identifiers, and a larger multi-source phishing test. The older corpus provides some of these slices, but new coverage must not be represented as exhaustive.
