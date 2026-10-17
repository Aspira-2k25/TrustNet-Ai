# Dynamic phishing URL audit

16 source-labelled URLs. Seed 20261016. Live protected collection enabled.
Provider reports may be wrong or stale. Reputation-enriched counts are not independent accuracy, because the positive sample comes from that provider.

Model-only counts: {'legitimate_false_alerts': 0, 'reported_phishing_alerts': 5, 'legitimate_total': 8, 'reported_phishing_total': 8}
Combined counts: {'legitimate_false_alerts': 0, 'reported_phishing_alerts': 8, 'legitimate_total': 8, 'reported_phishing_total': 8}

| URL (defanged) | Reference | Model estimate | Risk index | Result | Live checks | urlscan comparison |
|---|---|---:|---:|---|---|---|
| hxxp://49[.]51[.]43[.]12/v3/signin/identifier?amp%3Bfollowup=https%3A%2F%2Faccounts[.]google[.]com&amp%3Bifkv=AWnogHe_pDujLaO-hl3d_3DQFjS6PW6JGM3LRrD13mxmiaQWTJuHz9b6nwmaSIh76M5SMOelnJex7g&amp%3Bpassive=1209600&continue= | provider_reported_phishing | 0.982 | 100.0 | SUSPICIOUS | dns, http, html, reputation | UNAVAILABLE |
| hxxp://43[.]156[.]0[.]130/v3/signin/identifier?amp%3Bffgf=1&amp%3Bfollowup=https%3A%2F%2Faccounts[.]google[.]com&amp%3Bifkv=Af_xneGpinflONH_c3iB5WwVV1C6BSPwAwpudWnjxe8BcKRMcZLFgAnlzpjtHVk0QMFIUm6AcMYv&amp%3Bpassive=12096 | provider_reported_phishing | 0.982 | 100.0 | SUSPICIOUS | dns, http, html, reputation | NO_EXACT_REPORT |
| hxxp://www[.]allegrolokalnie[.]57162055[.]shop/ | provider_reported_phishing | 0.999 | 99.9 | SUSPICIOUS | dns, http, html, registration | UNAVAILABLE |
| hxxp://c53dbdbd[.]lighthousefilms[.]nl/?e476e&id=octopic[.]be | provider_reported_phishing | 0.842 | 84.2 | SUSPICIOUS | dns, http, html, registration | UNAVAILABLE |
| hxxp://yfdabv8[.]com/?dn=appgallery[.]ledgerliveapp[.]lol&accid=710956738&spfwd=1&spmsg=nscif | provider_reported_phishing | 0.252 | 98.5 | SUSPICIOUS | http, html, registration, reputation | NOT_QUERIED |
| hxxp://docusignappinstallers[.]help/ | provider_reported_phishing | 0.394 | 98.9 | SUSPICIOUS | registration, reputation | NOT_QUERIED |
| hxxp://pub-78a272af52b14a33975228017d07268d[.]r2[.]dev/index[.]html | provider_reported_phishing | 0.994 | 99.4 | SUSPICIOUS | dns, http, html | NOT_QUERIED |
| hxxp://bluesoftsdocrks[.]com/Docusign/page/ | provider_reported_phishing | 0.380 | 98.8 | SUSPICIOUS | registration, reputation | NOT_QUERIED |
| hxxps://www[.]google[.]com/ | legitimate_official_homepage | 0.162 | 16.2 | NO_STRONG_INDICATORS | dns, tls, http, html, registration, reputation | UNAVAILABLE |
| hxxps://github[.]com/ | legitimate_official_homepage | 0.206 | 20.6 | NO_STRONG_INDICATORS | dns, tls, http, html, registration | UNAVAILABLE |
| hxxps://mozilla[.]org/ | legitimate_official_homepage | 0.206 | 20.6 | NO_STRONG_INDICATORS | dns, tls, http, html, registration | NO_EXACT_REPORT |
| hxxps://khanacademy[.]org/ | legitimate_official_homepage | 0.094 | 9.4 | NO_STRONG_INDICATORS | dns, tls, http, html, registration | NO_EXACT_REPORT |
| hxxps://cloudflare[.]com/ | legitimate_official_homepage | 0.104 | 10.4 | NO_STRONG_INDICATORS | dns, tls, http, html, registration | NOT_QUERIED |
| hxxps://w3[.]org/ | legitimate_official_homepage | 0.094 | 9.4 | NO_STRONG_INDICATORS | dns, tls, http, html, registration | NOT_QUERIED |
| hxxps://google[.]com/ | legitimate_official_homepage | 0.240 | 24.0 | NO_STRONG_INDICATORS | dns, tls, http, html, registration, reputation | NOT_QUERIED |
| hxxps://gnu[.]org/ | legitimate_official_homepage | 0.010 | 1.0 | NO_STRONG_INDICATORS | dns, tls, http, html, registration | NOT_QUERIED |

5 invalid/non-HTTP inputs rejected with HTTP 422.
Exact source IDs/dates, model scores, observations, provider states and stored shared trust reports are in dynamic_url_audit.json.
