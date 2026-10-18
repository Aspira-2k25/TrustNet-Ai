# Phishing correction and independent comparison

The local phishing default is configured for `regional-v1`. Image/scam code is unchanged. This replaces the rejected raw-hostname candidate with URL-shape routing between the preserved v5 expert and a disagreement correction. There is no special verdict or score for Google, PayPal or another named website.

## What changed

Underlying fusion predictions for the correction were generated on calibration domains excluded from fitting both earlier fusion models. Correction fitting and isotonic calibration use separate domain groups. The regional expert/threshold search uses validation data and familiar-site regressions as explicit development constraints; those familiar sites are not an independent test. Unlike the initial regional search, it includes the existing model's operating point and permits different regional FPR budgets while enforcing a global budget and targeted recall constraints.

Selected routing:

| URL shape | Expert | Alert threshold |
| --- | --- | ---: |
| Root, no query | Preserved v5 | 0.70 |
| Any query | Preserved v5 | 0.70 |
| Non-root path, no query | Disagreement correction | 0.8292682926829269 |

The regional bundle manifest SHA-256 is `93e59ed0b126a902d00e109e998d4d0c61d6f0bca8ee37af89b3144d29a831e3`. Every component is checksummed. Thresholds and artifacts were frozen before opening the independent test. Research experiments v10–v16 remain rejected or superseded; their reports are retained for audit. No independent-test result was used to adjust the accepted candidate.

## Results and limits

| Independent test: 103 reference negatives, 50 provider positives | Previous v5 | Regional v1 |
| --- | ---: | ---: |
| False positives | 17 | 7 |
| Missed phishing | 18 | 17 |
| Accuracy | 77.12% | 84.31% |
| Phishing recall | 64% | 66% |
| F1 | 0.6465 | 0.7333 |
| Brier score | 0.2053 | 0.1569 |

Twelve previously wrong results became correct; one previously correct result became wrong. FPR is 6.80% and FNR is 34% on this small test, with wide uncertainty. Labels retain provider/reference uncertainty. These numbers demonstrate a relative improvement on the reserved sample, not broad production reliability or a completed real-world benchmark. Source/domain separation does not establish complete temporal/campaign separation.

These are model-only binary operating-point metrics. They do not include later review/abstention decisions or live forensic overrides.

The historical regression set improved from 91.608% to 91.800% accuracy, 0.964% to 0.906% FPR, and 29.230% to 28.665% FNR. New targeted validation false positives fell from 20 to seven, with six misses unchanged. The independent test is now consumed; its original integrity verification is a historical snapshot. Reserve a new independent test before subsequent tuning/acceptance.

Actual offline detection/event/report smoke checks pass for Google, GitHub and PayPal (no strong indicators), lookalike risk and a fresh intermediate-hop reputation fixture. Python documentation `/3/` remains a high-scoring review case rather than a phishing verdict; the score problem is not fully resolved. Report risk/trust indices are not proof of authenticity, and no confidence percentage is fabricated. Routing changes calibration, so the system explicitly does not claim an independently calibrated routed probability.

## Forensic fixes

Query inspection now records bare-host destination parameters such as `dn`, `domain`, `host` and `target`, protocol-relative targets, and full URL values under other parameter names. It never follows these inferred destinations or treats them alone as proof of phishing. No transport scheme is claimed for bare-host values.

Reputation checks now inspect up to two public observed intermediate hops in addition to the submitted/final URL. A reported intermediate destination cannot be hidden by a benign final page. Private destinations and credential-bearing targets are skipped; rate-limit responses stop additional lookups. Existing provider cache, freshness and daily quota still apply. Evidence identifies an intermediate match rather than falsely attributing it to the original or final URL.

Optional hop lookups are skipped once 12 seconds of collection have elapsed, including a second time check after DNS resolution, leaving time within the worker's 30-second collection RPC. This supplements request count and provider backoff bounds.

## Activation and rollback

The accepted bundle is `models/phishing_url/checkpoints/regional_v1/manifest.json`. Both phishing launchers select it by default. Docker Compose uses `PHISHING_MODERN_BUNDLE`, defaulting to `regional_v1`. To return to the preserved model:

```powershell
$env:PHISHING_MODERN_BUNDLE = 'modern_v5'
.\scripts\start-phishing-infrastructure.ps1
```

To select the regional bundle again, remove that environment override or set it to `regional_v1`. This rebuilds/restarts phishing and its infrastructure dependencies. It does not rebuild or restart image/scam detectors. Model artifacts remain local/ignored; another checkout needs the checked bundle restored before startup.

Local activation was completed: phishing worker `/ready` returned true, collector health passed, and the mounted manifest hash matched the frozen selection. Both containers were rebuilt with the optional-enrichment time bound. Linux inference reproduced the Windows regression results. Real Google and PayPal collections returned HTTP 200 with all listed live observations and no phishing verdict. Sixty-six Python tests, phishing report checks, TypeScript, targeted lint, Vite build and PowerShell parse checks passed. This does not claim a newly authenticated full Gateway/Kafka/browser scan. Submit a new scan; historical saved reports retain their original model results.

Reproduction commands are `train-phishing-residual.py`, `train-phishing-regional.py --expanded-budgets`, and the guarded one-shot `evaluate-phishing-regional-independent.py`; completed experiments refuse overwrite and the consumed test refuses a new fresh evaluation. `promote-phishing-regional.py` checks frozen development/independent acceptance before packaging. `smoke-phishing-regional.py` checks actual local inference and the report contract with recorded/mock evidence; it is not a live Gateway/Kafka browser test.

Remaining work: larger independently adjudicated and temporally separated cohorts; privacy/session-token and inactive-provider-record review in the next dataset revision; real benign documentation/authentication cases; better recall for compromised ordinary domains and redirects; routed-system calibration; full authenticated browser/Gateway/Kafka verification; live throughput and drift checks. Retain bounded live forensic evidence: URL text alone cannot reveal all malicious content behind an ordinary address.
