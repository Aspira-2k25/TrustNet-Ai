# Message and embedded-URL integration

## Data flow

1. Authenticated website/extension submits a `MessageInput` through Gateway and Scan Management.
2. Scam inference preserves the frozen DistilBERT/TF-IDF model, class probabilities, native score and text explanation.
3. URLs are extracted from plain text, HTML anchor destinations and structured displayed links. Duplicate literal URLs are assessed once. No destination is opened during a message scan.
4. At most eight links are checked, two concurrently, with a three-second request timeout and six-second total URL deadline. Excess, malformed, failed and missing checks remain visible.
5. The internal phishing service returns checked regional model results plus local link/impersonation evidence. Live website collection is separate and requires an explicit inspection request; it is not silently claimed for embedded links.
6. `message-url-max-v1` uses `max(message risk, available URL indices)`. A phishing URL alert escalates the verdict; URL review or missing URL checks prevents a clean low-indicator verdict. A benign URL never cancels a text alert.
7. Scan Management persists the result and history. Website, PDF and extension show the same verdict, separate scores and per-link coverage.

## Interpretation

The combined risk index is conservative decision fusion, not a trained/calibrated probability. The limited comparison below does not establish production accuracy. `native_score` and `metadata.probabilities` remain message-model outputs. `metadata.message_model` preserves its score, confidence and verdict. With links present, combined confidence is unavailable and the top-level confidence is zero; the original message confidence is displayed separately. Missing URL results have a null score and never become zero-risk evidence.

`metadata.fusion` records the policy, scores and number of links found/assessed. `metadata.links` records status, model version, URL risk, reasons and offline coverage. Message class labels can differ from the overall warning because the URL branch can independently trigger it. Sender identity and AI authorship remain unverified/unassessed.

## Evaluation boundaries

The scam model's existing held-out result (562/577, 97.40% accuracy) describes its original test, not this new fusion. Earlier independent-source scam evaluation was substantially weaker and must be disclosed. The selected phishing release's imported 313-row convenience test reports 90.73% accuracy, 92.91% precision, 87.33% recall and 90.03% F1, with uncertain provider labels and limited benign query coverage. Neither benchmark demonstrates universal reliability or publication superiority.

## Frozen source comparison, 18 October 2026

The unchanged deployed message model and offline URL/fusion policy were evaluated on the previously frozen 300-email HarmJ0y collection sample, 100 source records each labelled Phishing, Spam and Valid. Seven records were rejected by the existing English input guard, including five phishing and two spam records; these are exclusions, not correct predictions. The remaining 293 records contain 95 phishing and 198 non-phishing records. No normalized text/group overlap was found against the two supplied training CSVs. This audit cannot exclude unknown upstream overlap.

An alert means `LIKELY_SCAM` or `SUSPICIOUS`, not confirmed fraud. Spam is non-phishing for this binary comparison, not declared harmless. URL-only abstains without an assessed link. Compare all three methods on the same 127-email URL-assessed subset:

| Method, same 127 emails | Accuracy | Precision | Recall | F1 | TN / FP / FN / TP |
| --- | --- | --- | --- | --- | --- |
| Message only | 85.04% | 64.71% | 75.86% | 0.6984 | 86 / 12 / 7 / 22 |
| URL only | 62.20% | 31.37% | 55.17% | 0.4000 | 63 / 35 / 13 / 16 |
| Conservative fusion | 62.99% | 37.14% | 89.66% | 0.5253 | 54 / 44 / 3 / 26 |

Across all 293 accepted emails, message-only accuracy/precision/recall/F1 were **85.32% / 72.81% / 87.37% / 0.7943** (TN167, FP31, FN12, TP83). Fusion returned **75.77% / 58.00% / 91.58% / 0.7102** (TN135, FP63, FN8, TP87). URL-only covered 127/293 emails, or 43.34%; its subset accuracy must not be compared directly to all-email message accuracy. Four accepted emails had incomplete link coverage, retained explicitly by the deployed policy.

Fusion recovered four additional phishing alerts while adding 32 false alerts. Its non-phishing false-positive rate increased from 15.66% to 31.82%. This is a recall versus false-positive tradeoff, **not an accuracy improvement**. False alerts can arise from the conservative missing-check review policy as well as URL model/domain warnings. A separate validation collection and untouched follow-up test are required before changing that policy or promoting a new threshold. The current result does not justify a 97% combined-system accuracy claim.

This source had already been inspected in earlier work, so this is not a new untouched prospective test. It combines author-curated human and LLM-origin examples with uncertain real-world provenance. No model training, calibration, threshold tuning or checkpoint selection was performed in this comparison. Website live inspection is separate and was not evaluated for classification accuracy. The earlier weak independent-source SMS baseline, 70.734% accuracy and macro-F1 about 0.556, remains a historical limitation and uses a different task/test protocol.

Aggregate counts, provenance, checksums and exclusions count are retained in `models/scam_message/evaluation/message-url-fusion-20261018.json`. The reproducible harness is `scripts/research/evaluate-message-url-fusion.py`; it requires the external frozen JSON/manifest and training CSVs via explicit arguments. Raw source emails and row-level outputs remain outside the application and are not redistributed. There is no runtime dependency on those files.

## Explicit website inspection

After a message is saved, **Inspect this URL** on the website or Gmail panel requests a separate snapshot. The backend contacts the destination only for this explicit action. The authenticated endpoint is `POST /api/v1/scans/{scan_id}/links/{link_index}/inspection` with body `{}`. It resolves the URL from the owner's saved message, accepts no caller-provided URL, and limits inspection to the eight supported link positions. Other users cannot inspect another owner's scan.

The internal phishing `/inspect` endpoint delegates to the existing protected collection pipeline. DNS/IP filtering, pinned destinations, certificate verification, bounded redirects and response sizes remain in force. Only static HTML is inspected. No JavaScript is executed or forms submitted. Collection capacity is bounded; unavailable services produce an explicit retryable state, never a safe verdict.

Evidence separates observed domain/IP/certificate/page facts, explanations of their significance, learned model assessment, and unavailable checks. Domain age, HTTPS and clean reputation results do not establish legitimacy. Each snapshot has its own risk assessment and timestamp. The original quick message/URL score remains unchanged. A completed snapshot is reused rather than silently refreshed, so it does not represent continuous monitoring.

`link_inspections` is an additive table created by the existing database initialization. Inspection snapshots survive history loads, appear in message PDFs, and are stored separately from the original assessment. Failed attempts can be retried; concurrent duplicates receive 409 and stale claims can be recovered after 90 seconds.

Regression checks:

```powershell
.\.venv\Scripts\python.exe -m pytest services/scan_management/tests/test_link_inspection.py shared/tests/test_url_inspection.py -q
node --test extensions/trustnet-mail/tests/worker.test.cjs
.\.venv-scam\Scripts\python.exe scripts/checks/verify-integration.py --inspect --require-live
```

The last command needs the running full stack and working collector. Omit `--require-live` to test explicit degradation without requiring live website observations. Browser fixtures are automated adapter tests, not proof of live Gmail compatibility. Real Gmail verification was skipped at the user's request; Edge and other browsers have not received a live installation test.
