# Phishing URL functional test results

25 varied addresses and 5 invalid inputs. Seed: 42. No URLs fetched. No verified ground truth; these predictions are not an accuracy benchmark.

**Reliability finding:** several familiar public homepage addresses received high phishing scores. The frozen training split has zero legitimate HTTPS examples and only six phishing HTTPS examples. HTTPS confidence is withheld; scores remain experimental. Retraining and representative HTTPS validation are required.

| URL | Verdict | Trust score / 100 (higher = risk) | Confidence | Inference ms |
|---|---|---:|---:|---:|
| `https://www.google.com/` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 1108 |
| `https://www.wikipedia.org/` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 117 |
| `https://github.com/` | Low phishing signal | 1.0 | Unavailable (coverage) | 1417 |
| `https://www.microsoft.com/` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 492 |
| `https://www.amazon.in/` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 1044 |
| `https://www.python.org/` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 684 |
| `https://www.bbc.com/news` | Low phishing signal | 3.0 | Unavailable (coverage) | 674 |
| `https://www.paypal.com/signin` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 737 |
| `https://example.com/` | Low phishing signal | 1.0 | Unavailable (coverage) | 1648 |
| `https://example.com/account` | Phishing risk detected | 100.0 | Unavailable (coverage) | 621 |
| `https://account-0409.example/billing?id=32098` | Phishing risk detected | 100.0 | Unavailable (coverage) | 1040 |
| `https://verify-2286.example/login?id=88696` | Phishing risk detected | 100.0 | Unavailable (coverage) | 1195 |
| `https://account-9674.example/help?id=4165` | Phishing risk detected | 100.0 | Unavailable (coverage) | 702 |
| `https://account-1535.example/index?id=30495` | Phishing risk detected | 100.0 | Unavailable (coverage) | 384 |
| `https://account-9195.example/index?id=93850` | Phishing risk detected | 100.0 | Unavailable (coverage) | 1196 |
| `https://news-3611.example/help?id=77236` | Low phishing signal | 5.0 | Unavailable (coverage) | 1271 |
| `https://secure-0106.example/index?id=91506` | Phishing risk detected | 100.0 | Unavailable (coverage) | 1223 |
| `https://news-5574.example/billing?id=20379` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 771 |
| `https://verify-5514.example/login?id=12156` | Phishing risk detected | 100.0 | Unavailable (coverage) | 905 |
| `https://news-1584.example/billing?id=45082` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 2003 |
| `http://192.0.2.1/login` | Phishing risk detected | 100.0 | 100.0% | 428 |
| `https://paypal.com@account.example/login` | Phishing risk detected | 100.0 | Unavailable (coverage) | 829 |
| `https://xn--pple-43d.example/` | Phishing risk detected | 100.0 | Unavailable (coverage) | 673 |
| `https://shop.example:8443/a%2Fb?q=hello%20world` | Assessment uncertain | Unavailable (models disagree) | Unavailable (coverage) | 1443 |
| `https://example.com/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` | Phishing risk detected | 99.0 | Unavailable (coverage) | 758 |

All 5 malformed/non-HTTP inputs rejected with HTTP 422.
All valid results passed the shared result, explanation, evidence/analysis, coverage, scan-ID and persisted trust-score contract checks.
