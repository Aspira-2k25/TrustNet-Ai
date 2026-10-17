# Dynamic phishing detection

The current pipeline uses **modern-v5** with policy **dynamic-v2**. It replaces the previous HTTPS abstention and fixed forensic-score policy. No domain safety allowlist, named-brand verdict table or constant 75-point alert is used.

## What a scan does

1. Validate an absolute HTTP(S) URL and normalise its empty root path to `/`, preserving path encoding, query and fragment.
2. Evaluate a calibrated CPU ensemble. Registered-domain identity is masked in the text branch; subdomain/path/query/fragment and separately learned structural features remain available. The model cannot mark Google safe simply because its name appears in a table.
3. Request live observations from an authenticated isolated collector: public DNS, TLS hostname validation, bounded redirects and static HTML/password forms, RDAP registration age and reputation reports.
4. Combine the model estimate with recorded forensic findings. Strong URL deception, credential exposure and a fresh exact reputation match can raise the risk index. Evidence updates are individually recorded.
5. Return the existing shared detection/trust-score contract, plain reasons, collection coverage and report/PDF data.

## Score meaning

The model is calibrated on domain-disjoint development data. The **combined 0–100 score is an evidence-weighted risk index**, not a calibrated probability or a guarantee of safety. Higher means greater risk, matching the shared trust engine. Policy weights are explicit in `models/phishing_url/configs/evidence_policy.json`; these weights are not claimed to be learned probabilities. Identical forensic findings do not force an identical score, because the model estimate also contributes.

The original BERT/LightGBM v1 and rejected candidates remain preserved for research. Their unsupported probabilities do not silently become current assessments. Invalid inputs or complete detector failure still produce an incomplete result; normal HTTPS is not rejected as a class.

## Live collection and reputation

Normal Docker startup enables the collector automatically and generates a local authentication token under ignored `runtime_state/phishing/`. The collector joins a dedicated worker link and egress network, never the Kafka/Mongo service network. Fetches validate every redirect, pin public destination addresses and validate TLS. Private destinations, unsafe ports and credential-bearing fetches remain blocked. No certificate validation is bypassed.

Static pages are size bounded; oversized pages are truncated and marked partial. JavaScript and form submissions are not executed. Observation absence does not establish safety.

PhishStats is queried with the **hostname only** using its indexed `host` equality filter; exact canonical URL matching is local, preserving path/query distinctions. Matching hostnames alone never flag a URL. A current alert requires a high-score report within seven days; historical matches remain distinct. Redirect destinations can be checked separately. Bulk audits can prefetch up to ten requested hosts in one OR query; only actual provider rows enter the ordinary per-host cache, never input labels. Truncated combined results are not cached as misses.

The cache and quota ledger persist across collector restarts. Cache TTL is 90 minutes, with a conservative 45-request daily local budget for anonymous access. Provider limits, failures and no-match responses are distinct. No match is not a clean verdict. Optional `PHISHSTATS_API_KEY` configuration is supported; provider credentials are never returned in scan results.

## Running

```powershell
.\scripts\start-phishing-infrastructure.ps1
```

This starts the current CPU model and live collector. No CUDA, Colab or BERT download is required. `-Offline` explicitly disables collection. `-Baseline` selects the preserved research baseline, whose v1 probabilities remain quarantined. Old scan IDs retain their historical payloads: refresh the frontend and submit a new scan.

## Validation and limits

### Certificate signatures and navigation

Normal verified TLS handshakes authenticate the certificate chain, validity period and destination hostname. The collector records the leaf's SHA-256 fingerprint, issuer/subject, signature hash/OID, public-key type/size, validity dates and negotiated TLS/cipher. Weak hashes/keys or failed validation request review; no insecure fallback is used. Revocation and certificate transparency are not checked. A valid signature, a recognised issuer or a short-lived certificate does not establish whether page content is phishing.

The bounded request records each observed redirect hop and its path/status/certificate. Forensics inspects intermediate HTTPS downgrades and repeated registered-domain transitions. Local path analysis includes encoded dot segments, double encoding and explicit redirect/navigation parameters. Parameters are not followed, arbitrary page links are not crawled, and a normal external sign-in parameter is informational. No files are downloaded for executable/code-signature analysis.

See `docs/phishing/audit-2026-10-16.md`, the model card and `models/phishing_url/research/dynamic_url_audit.md`. Dataset test recall is about 70.8%; model-only detection remains incomplete. The text fit reached its 25-iteration cap and emitted a convergence warning. Further optimisation, independently labelled temporal evaluation, higher-capacity reputation access, script-rendered phishing coverage and calibration of the combined policy remain necessary. Source benchmark metrics and a small web sample do not establish superiority to commercial services.
