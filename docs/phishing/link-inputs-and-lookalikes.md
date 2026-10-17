# Domain and link inspection — 17 October 2026

The previous URL-text model deliberately masked registered-domain identity to reduce memorised domain predictions. Consequently its output alone could not reliably distinguish visually similar names such as `paypal.com` and `paypaI.com` (canonical hostname `paypai.com`). A separate generic forensic check now covers that gap. The original spelling and canonical hostname are both retained; ordinary domain capitalization does not change identity.

## Accepted inputs

Bare domains, IP literals, host/port/path strings and scheme-relative links are normalised to HTTPS for the web scan. Explicit HTTP/HTTPS links keep their transport and case-sensitive path/query. The original submission remains in the scan record. Malformed hostnames, invalid ports, controls, whitespace and backslashes remain rejected.

Other URI schemes are inspected offline. Hierarchical links such as FTP/custom app links and single-recipient mailto links expose a hostname for destination/visual-identity checks. File, script, data, telephone and opaque app links are never opened or executed. The web model, TLS/page collector and web reputation calls are not applied to these links. A strong offline indicator can produce a disclosed forensic risk index; otherwise the report explains that a reliable website legitimacy score cannot be assigned. Accepting a URI is not a promise that every protocol can be classified as real/phishing from a web model.

The collector's strict HTTP/HTTPS parser and public-address/port restrictions remain unchanged. Generic input handling is a separate layer; accepting `file:` or `javascript:` at the scan form does not grant the collector permission to follow it.

## Generic visual-domain comparison

The bundled reference derives from the first 10,000 [Majestic Million](https://majestic.com/reports/majestic-million) ranked domains (Majestic, CC BY 3.0) and the [Unicode confusables dataset](https://www.unicode.org/Public/security/latest/confusables.txt). Source hashes, retrieval time and attribution accompany `configs/domain_reference.json`; full notices are in `domain_reference_LICENSE.txt`.

Registered domains are decoded from IDNA and mapped through Unicode confusable characters, with an additional disclosed i/l/1 font-ambiguity mapping. References need a first label of at least five characters. A collision must be a different registered domain; when both names are ranked, the reference must be more than ten times higher ranked. Ordinary spelling/capitalization of the same domain does not trigger the warning. Paths mentioning a brand do not become domain-impersonation evidence.

The same comparison applies to observed redirect destinations, so an unremarkable short URL can still reveal a visually deceptive destination. A match records both names, reference provenance and why they differ. It raises an explicitly uncalibrated evidence index (generic weight 0.80); web scores also retain the underlying model estimate. This is not a hardcoded PayPal exception or a dictionary of domain verdicts. Inclusion in the ranking never bypasses model or forensic checks, establishes ownership, or declares a URL safe. Similarity can also occur for benign/defensively registered domains; the report says impersonation **risk**, not confirmed malicious ownership.

Refresh the source data and restart phishing services to load a new snapshot:

```powershell
.\.phishing-test-venv\Scripts\python.exe scripts/update-phishing-domain-reference.py
.\scripts\start-phishing-infrastructure.ps1
```

The ranking is not a benign-domain ground truth. Coverage is finite; unknown brands, arbitrary spelling edits and different-TLD imitations can be missed. The i/l/1 extension is a font heuristic rather than an exact UTS39 implementation. Rank and evidence weights require independent false-positive evaluation. This change does not resolve the previously documented documentation-path model false positive.

## Reports and validation

New results carry `link_analysis_version=links-v1`. Earlier phishing reports require a new scan; their immutable payloads are not rewritten. Only phishing display/routing and its URL-request validator change; image/scam detector code is preserved.

Regression coverage includes bare inputs, original/canonical spelling, valid capitalization, Unicode/digit substitutions, a synthetic reference proving generic behaviour, same-model/different-forensic outcomes, redirect destinations and non-web no-fetch enforcement. The authenticated async regression script is `scripts/test-phishing-link-inputs.py`; persisted results are written to `models/phishing_url/research/link_input_regression.json`. These tests establish the specified behaviours, not universal phishing accuracy.

Final verification: **71 targeted tests passed**, frontend TypeScript/production build passed, and **11/11 authenticated async cases completed** through Gateway, Kafka, the deployed worker, MongoDB and isolated relational report storage. Observed scores: bare/explicit `paypal.com` 20.6 LOW, `paypaI.com` and lowercase `paypai.com` 84.1 with a visual-domain warning, `app1e.com` 87.9, scheme-relative Google 16.2 LOW. FTP/mailto lookalikes produced 80-point forensic-only indices. Ordinary mailto, script and file inputs remained unknown with no invented numerical legitimacy score and no network collection.

Kafka and MongoDB had been stopped before this turn; the first smoke attempt could not reach them. Their existing containers were started without recreating databases, and the subsequent full run passed. Image/scam detector services were not modified. The main UI's Scan Management backend on port 8002 was not running at the final check; normal application startup must load the updated phishing request validator. The successful regression used isolated authenticated test servers, not a claim that the full UI stack was launched.
