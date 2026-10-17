# Phishing URL functional test results

8 varied addresses and 5 invalid inputs. Seed: 42. No URLs fetched. These predictions are not an accuracy benchmark.

**Policy:** forensic indicators are evaluated alongside model diagnostics. Unsupported v1 HTTPS model scores are withheld. Strong forensic findings use an explicitly uncalibrated severity index, not a phishing probability. This functional suite does not establish accuracy.

| URL | Verdict | Trust score / 100 (higher = risk) | Confidence | Inference ms |
|---|---|---:|---:|---:|
| `https://www.google.com` | Assessment uncertain | Unavailable (uncertain) | Unavailable (coverage) | 12231 |
| `https://www.google.com/` | Assessment uncertain | Unavailable (uncertain) | Unavailable (coverage) | 828 |
| `https://google.com` | Assessment uncertain | Unavailable (uncertain) | Unavailable (coverage) | 873 |
| `https://google.com/` | Assessment uncertain | Unavailable (uncertain) | Unavailable (coverage) | 824 |
| `https://www.wikipedia.org/` | Assessment uncertain | Unavailable (uncertain) | Unavailable (coverage) | 1079 |
| `https://github.com/` | Assessment uncertain | Unavailable (uncertain) | Unavailable (coverage) | 1007 |
| `https://example.com/account` | Assessment uncertain | Unavailable (uncertain) | Unavailable (coverage) | 854 |
| `https://paypal.com@account.example/login` | Suspicious forensic indicators | 75.0 (forensic_rule_severity) | Unavailable (coverage) | 924 |

All 5 malformed/non-HTTP inputs rejected with HTTP 422.
All valid results passed the shared result, explanation, evidence/analysis, coverage, scan-ID and persisted trust-score contract checks.
