# Phase 0 — phishing requirements and research gates

Scope: credential-theft and malicious-redirection phishing from submitted HTTP(S) URLs. Internal labels are 1=phishing and 0=legitimate. Generic malware, email classification and image detection are outside this module.

## Required progression

UCI pre-extracted-feature LR/RF experiments are offline research only. Primary raw-URL LR/RF baselines precede independently trained LightGBM and BERT branches. Their validation-derived weighted vote, calibration and threshold form the main deployable milestone. GNN follows later. Existing lexical baseline scaffolding does not replace this progression.

Inputs retain original URL encoding/path/query case. Collect WHOIS/registration, DNS and TLS only through a service-owned safe collection boundary. Optional HTML collection is disabled until bounded fetch, address pinning, redirect revalidation and collector network isolation are verified. Never execute scripts or submit forms. Missing age is missing, not zero; HTTPS is not proof of legitimacy.

## Operating objective

Report both missed phishing and false alarms. Compare validation F1 with a high-recall operating point and its false-positive rate. The current baseline trainer selects validation F1 only; final promotion requires the measured precision/recall tradeoff, grouped uncertainty and calibrated probabilities. Test labels cannot select threshold, weighting, calibration or features. Confidence remains explicitly unavailable until its convention is evaluated.

## Sources and data decisions

- UCI: https://archive.ics.uci.edu/dataset/327/phishing — downloaded official archive; CC BY 4.0; 30 pre-extracted features. Audit results live in `models/phishing_url/research/uci_audit.json`. Original target direction still requires an authoritative label dictionary; UCI metadata does not explain it. Do not infer direction from numeric sign or class majority.
- Approved primary: https://www.kaggle.com/datasets/taruntiwarihp/phishing-site-urls — user selected this release. Official Kaggle API reports version 1, updated 21 July 2020, license name Database: Open Database, Contents: Database Contents. Its description explicitly defines good as non-phishing (internal 0), bad as phishing (internal 1). Archive and metadata downloaded; preparation report pins their hashes. Original collection lineage is not supplied by the uploader. Scheme-less rows are parsed with assumed HTTP and retain original text plus scheme_inferred provenance; this is not observed transport.
- PhishTank: https://phishtank.org/developer_info.php — verified online phishing feed, hourly refresh; descriptive user agent required; repeated downloads need application key. Feed absence is not a legitimate label. Preserve verification and acquisition times. Feed licensing/terms and snapshot hash pending acquisition.
- Legitimate freshness source: https://tranco-list.eu/ — ranking alone is not a page-level legitimate label. Pin list ID/date, document URL construction and labeling, and remove overlap with training domains.
- Alternative: https://data.mendeley.com/datasets/c2gw7fy2j4/3 — version 3, 25 June 2021, CC BY 4.0, 11,430 URLs and 87 extracted features. Keep separate from UCI and lexical URL experiments; downloaded counts/hash/labels pending.

## Acceptance checklist

- [x] Threat, input and internal positive class defined.
- [x] Required model progression preserved.
- [x] Optional collection disabled pending safe boundary.
- [x] Official UCI release acquired and hashed.
- [ ] Original dataset label meanings confirmed for each imported release.
- [x] Primary dataset selected and version/license/label metadata acquired.
- [x] Primary file hashes and exclusion/split audit recorded; missing source lineage documented for evaluation.
- [ ] Freshness and alternative dataset access/terms resolved.
- [ ] Reference-paper comparison finalized with reproducible input/voting details.
- [ ] Validation operating-point comparison and promotion policy evaluated.

Phase 0 is in progress. Later scaffolding may be prepared, but no trained primary-model milestone or production deployment is accepted before these gates are resolved.
