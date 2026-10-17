# Phishing URL functional test results

5 varied addresses and 5 invalid inputs. Seed: 42. No URLs fetched. These predictions are not an accuracy benchmark.

**Reliability finding:** several familiar public homepage addresses received high phishing scores. The frozen training split has zero legitimate HTTPS examples and only six phishing HTTPS examples. HTTPS confidence is withheld; scores remain experimental. Retraining and representative HTTPS validation are required.

| URL | Verdict | Trust score / 100 (higher = risk) | Confidence | Inference ms |
|---|---|---:|---:|---:|
| `https://www.google.com/` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 4659 |
| `https://google.com/` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 253 |
| `https://www.wikipedia.org/` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 1088 |
| `https://github.com/` | Low phishing signal | 1.0 | Unavailable (coverage) | 936 |
| `https://example.com/account` | Phishing risk detected | 100.0 | Unavailable (coverage) | 546 |

All 5 malformed/non-HTTP inputs rejected with HTTP 422.
All valid results passed the shared result, explanation, evidence/analysis, coverage, scan-ID and persisted trust-score contract checks.
