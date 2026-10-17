# Dynamic phishing URL audit

4 source-labelled URLs. Seed 20261016. Live protected collection enabled.
Provider reports may be wrong or stale. Reputation-enriched counts are not independent accuracy, because the positive sample comes from that provider.

Model-only counts: {'legitimate_false_alerts': 1, 'reported_phishing_alerts': 0, 'legitimate_total': 4, 'reported_phishing_total': 0}
Combined counts: {'legitimate_false_alerts': 1, 'reported_phishing_alerts': 0, 'legitimate_total': 4, 'reported_phishing_total': 0}

| URL (defanged) | Reference | Model estimate | Risk index | Result | Live checks | urlscan comparison |
|---|---|---:|---:|---|---|---|
| hxxps://www[.]google[.]com/search?q=security | legitimate_official_url | 0.038 | 3.8 | NO_STRONG_INDICATORS | dns, tls, http, html, registration, reputation | NOT_QUERIED |
| hxxps://github[.]com/openai | legitimate_official_url | 0.306 | 30.6 | REVIEW_RECOMMENDED | dns, tls, http, html, registration | NOT_QUERIED |
| hxxps://docs[.]python[.]org/3/ | legitimate_official_url | 0.937 | 93.7 | SUSPICIOUS | dns, tls, http, html, registration | NOT_QUERIED |
| hxxps://en[.]wikipedia[.]org/wiki/Phishing | legitimate_official_url | 0.004 | 0.4 | NO_STRONG_INDICATORS | dns, tls, http, html | NOT_QUERIED |

0 invalid/non-HTTP inputs rejected with HTTP 422.
Exact source IDs/dates, model scores, observations, provider states and stored shared trust reports are in dynamic_url_audit.json.
