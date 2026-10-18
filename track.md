# Phishing detection implementation — nirmala

## Current accuracy/recall improvement — 18 October 2026

- [x] Added monotone second-expert rescue: preserve all primary alerts, use high model-score boundaries for additional root/query detections, and keep path-only behavior unchanged. No runtime domain allowlist, new GPU requirement or changes to learned component weights.
- [x] Selected the candidate on development data with targeted/reference false-alert guards and known-site score margins. Validation: 242 additional detections, zero extra false alerts; accuracy 90.08% → 90.65%, recall 71.31% → 73.14%.
- [x] Historical regression: 510 additional detections with two additional false alerts; accuracy 91.80% → 92.22%, recall 71.34% → 72.95%. Additional false alerts remained within the predeclared bound.
- [x] Reserved a new test excluding all old raw-source/evaluated domains and known distinctive path groups. Expanded before predictions with verified legitimate query links: 313 URLs, 163 references/35 domains, 150 provider positives/147 domains, including 13 benign queries/five domains. No reported phishing page was visited or model prediction used as a label.
- [x] Froze candidate bundle and performed one independent comparison: accuracy 90.10% → 90.73%, recall 86.00% → 87.33%, false alerts unchanged at 10, misses 21 → 19. All acceptance gates passed; the child test and overlapping parent are consumed. Earlier 66% recall belongs to a different test and is not the baseline for this comparison.
- [x] Packaged regional-recall-v1 with checksums and preserved regional-v1/modern-v5 rollback bundles. Updated phishing-only loading, launcher defaults and report explanation of second-expert alerts. Actual offline inference/event/report smoke passed for known roots, lookalikes, both rescue routes and a threat-report fixture.
- [x] Relevant Python regressions: 69 passed. Phishing frontend report tests, TypeScript and targeted lint passed.
- [x] Frontend production build passed. Running phishing worker is ready and reports regional-recall-v1 with the accepted manifest hash. Linux inference and live Google/PayPal collection/report checks passed (HTTP 200); Google registration evidence was unavailable. Recorded in `models/phishing_url/research/recall_deployment_20261018.json`.
- [ ] Larger adjudicated datasets, broader benign query/auth coverage, new independent acceptance data for future tuning, routed/rescue calibration and full authenticated browser/Gateway/Kafka verification. Current fresh test still has 19/150 misses and 10/163 false alerts; documentation-path review score remains unresolved.

Details: `docs/phishing/recall-improvement-2026-10-18.md`. Image/scam sources remain unchanged; work stays on nirmala.

## Current correction and deployment — 18 October 2026 (supersedes earlier pending entries)

- [x] Replaced the rejected raw-hostname candidate with a checked regional expert bundle. URL shape selects v5 for root/query links and the out-of-fit correction for path-only links; no named-domain allowlist or verdict override was added.
- [x] Enforced known-site development regressions, global validation FPR and targeted recall gates. Fixed regional search coverage by including the existing query expert's operating point. All development gates passed before opening the new test.
- [x] Froze artifacts/routing/thresholds, then consumed the 153-row independent test once: false positives 17 → 7, misses 18 → 17, accuracy 77.12% → 84.31%. Twelve old errors corrected, one new error. Small provider/reference test; no production-certification claim or post-test tuning.
- [x] Historical regression: FPR 0.964% → 0.906%, FNR 29.230% → 28.665%. Targeted development false positives 20 → 7 with six misses unchanged. Dataset registry and consumption marker updated; reserve a new test before later tuning acceptance.
- [x] Added checked regional loading, per-URL-shape thresholds, honest calibration metadata and matching phishing-only advanced report text. Preserved modern-v5 artifacts for rollback; default phishing launchers now select regional-v1.
- [x] Expanded offline destination inspection and bounded reputation checks for observed intermediate redirect hops. Query destinations are never fetched solely because they appear in a parameter. Public-address checks, quota/backoff and an optional-enrichment time bound remain enforced.
- [x] Passed 66 relevant Python tests, actual local inference/event/report smoke, phishing report regression checks, TypeScript, targeted lint, Vite production build, PowerShell parse and Git whitespace checks.
- [x] Rebuilt only phishing worker/collector containers (Kafka/Mongo dependencies started). Worker `/ready` true, collector healthy, loaded regional-v1 manifest hash verified. Linux matches local Google/GitHub/PayPal/doc-path regression outputs. Live Google and PayPal checks returned HTTP 200 with DNS/TLS/page/registration/reputation observations and no phishing verdict.
- [x] Branch remains nirmala. Image/scam detector sources and original modern-v5 model hashes preserved. No commit/push performed. Existing saved reports are historical; submit a new scan to use regional-v1.
- [ ] Improve remaining false positives/misses, including the high model risk/review result on Python documentation; add reviewed active/compromised-site labels and representative benign paths. The independent test still has 7/103 false positives and 17/50 misses.
- [ ] Establish routed-system calibration and larger temporal/domain/campaign-aware evaluation. Reserve a genuinely new independent test; the previous test is consumed.
- [ ] Full authenticated browser → Gateway → Kafka scan/report verification, throughput/drift assessment and an exercised rollback drill. Worker broker readiness/live collection are verified, not a new authenticated full-system scan.

Details: `docs/phishing/regional-correction-2026-10-18.md`; aggregate acceptance/deployment reports: `models/phishing_url/research/regional_*20261018.json`.

## Targeted retraining implementation — 18 October 2026

- [x] Added isolated, reproducible targeted structural retraining, validation-only fusion selection, fixed targeted-example weighting, immutable artifacts and frozen selection hashes. Independent-test inputs are excluded from both training commands.
- [x] Completed v8 on 516,006 training records. Historical FPR improved from 0.964% to 0.332%, but FNR worsened from 29.230% to 40.846%; rejected without deployment. Familiar-homepage checks passed.
- [x] Added a hash-verified targeted validation diagnostic: on 62 reference and 17 provider-positive URLs, v8 reduced false positives from 20 to 10 but increased false negatives from six to seven. These development results are not independent accuracy claims.
- [x] Implemented complementary targeted text training with a class-balanced sample plus every targeted training example, bounded text/fusion weighting, unweighted calibration and explicit historical/reference/homepage/targeted/convergence gates.
- [x] Dataset isolation, threshold-tie/FPR selection and domain-masking regressions: 16 tests passed. Python syntax and Git whitespace checks passed.
- [x] Completed v9 complementary training (160,158 sampled/targeted rows) and regression. Historical accuracy improved from 91.608% to 92.722%, FPR 0.964% to 0.566%, FNR 29.230% to 26.108%. Rejected for deployment: Google/GitHub/PayPal homepage false alerts and targeted validation FNR regression (six to seven misses). No independent-test URLs were scored.
- [x] Kept both research candidates isolated, preserved all active artifact hashes and verified no protected image/scam detector diff. Recorded the reasons and remaining gaps in the targeted training report; no runtime switch or branch change.
- [ ] Independent research-test evaluation, larger reviewed cohorts and complete live-policy/deployment acceptance remain required for promotion.

Details: `docs/phishing/targeted-training-2026-10-18.md`. Active model and image/scam modules remain unchanged.

## Targeted dataset and independent reservation — 18 October 2026

- [x] Collected public evidence from two curated official-origin batches and nine successful PhishStats pages. PhishTank access failed and the next PhishStats page returned 429; attempts were recorded and collection stopped. No reported phishing pages were visited and no model predictions supplied labels.
- [x] Built `targeted_20261018_v2`: 565 accepted targeted examples (209 train, 50 calibration, 79 validation, 74 regression references, 153 new test records), with source-tier provenance and observed reference-page/TLS evidence. Raw URL records remain ignored by Git.
- [x] Retained 610,916 usable historical development examples. Final development exports: train 516,006; calibration 53,061; validation 42,187. Historical regression remains separate (120,560 rows); old evaluation domains were not recycled into the new test.
- [x] Reserved an unscored independent research test with 103 legitimate/reference URLs across 25 domains and 50 provider-reported phishing URLs across 48 domains. Zero overlap with all original URL-source domains and earlier challenges. Known specific-path campaign groups are separated; full campaign/temporal independence is not claimed.
- [x] Preserved the undersized v1 reservation without scoring it, then expanded/revised the reservation before any retraining. The v2 test meets the unchanged minimum research coverage gate. Data integrity is not a production accuracy certification.
- [x] Verified frozen hashes, counts, complete provenance, learning/test domain/URL/known-group separation and canonical labels against both complete original corpora. Added a loader that rejects test/regression data for fitting and checks verification/hash gates.
- [x] Registered the candidate dataset and documented source terms, two-column exports, evidence tiers, privacy/duplicate exclusions and next-training protocol in `docs/phishing/targeted-dataset-2026-10-18.md`.
- [x] Final checks: 16 dataset/research/masking tests passed, development-loader smoke passed, Python syntax/whitespace checks passed, canonical label audit found zero conflicts, and all four active model hashes remained unchanged. Image/scam detector diff stayed empty.
- [ ] Retrain and select candidates using development splits only; pass older regression/homepage checks before opening the new independent test. Collect broader independently reviewed labels and additional fresh internationalized/lookalike/shared-hosting examples. Active modern-v5 and image/scam implementations remain unchanged.

## Model performance experiment — 18 October 2026

- [x] Verified official PhiUSIIL label mapping and reconstructed original source/domain partitions. Quarantined 45 conflicting URL keys. Kept historical evaluation explicitly labeled a reused regression benchmark.
- [x] Froze a separate local research challenge with 300 provider-reported phishing URLs and 507 official-page reference negatives. Recorded source hashes, collection times, label provenance and limitations. No phishing pages were opened; proprietary feed data remains under ignored data paths.
- [x] Removed fresh-challenge domains from all candidate fitting/selection partitions (698 training rows excluded). Candidate structural training has 516,247 available rows before its separate early-stopping partition. Dataset manifest records zero cross-partition domain overlap and legacy-domain overlap in the fresh collection.
- [x] Added a CPU candidate pipeline with source/class balancing, longer text convergence budget, full-structure fusion, separate isotonic calibration and validation-only maximum-recall threshold selection under a 1% FPR cap.
- [x] Five research integrity tests passed: tied-score handling, FPR budget enforcement, private-suffix domain grouping, balanced class/source mass and single-class metric reporting. Syntax/whitespace checks passed.
- [x] Completed v6 fitting and locked evaluation; rejected its selected threshold retune because FNR worsened despite lower FPR. Newly trained branches did not outperform retuned-v5 validation recall at the fixed cap. The text branch converged without the old warning.
- [x] Completed a complementary v7 experiment using existing branches plus regularized hostname text and HGB fusion. Historical accuracy improved 91.61% → 92.71%, FPR 0.964% → 0.610%, FNR 29.15% → 25.97%; however, challenge misses remained 133/300 and three familiar homepages regressed (Google/GitHub/PayPal). Candidate rejected for activation; no hard-coded domain exceptions added.
- [x] Saved aggregate metrics, source/error slices, strict legacy-unseen-domain challenge results, thresholds, candidate artifacts and 19-homepage regression evidence. Detailed findings and rejected-promotion rationale are in `docs/phishing/performance-improvement-2026-10-18.md`.
- [ ] Collect broader independently labeled hard-negative/authentication and recent phishing development data; freeze a new independent acceptance set before further selection. Improve root-path and recent long-path campaign recall without hostname-identity bias. Validate full live policy, calibration and deployment regression/rollback before switching models.
- [x] Active modern-v5 artifacts remain unchanged; no image/scam/shared-runtime source was modified by these experiments. Branch stays `nirmala`; no commit/push performed.
- [x] Final verification: nine research/masking tests, Python syntax and Git whitespace checks passed. All four active artifact hashes match their starting values. Saved explicit non-promotion decision in `models/phishing_url/research/acceptance_20261018.json`.

## URL-specific plain-language report — 17 October 2026

- [x] Replaced the default generic workflow with recorded per-URL findings: address structure, destination identity, path/navigation parameters, DNS addresses, verified certificate details, final page/status/redirects, password-form actions, registration age and exact-URL reputation. Missing and truncated evidence is explicitly identified.
- [x] Added a URL-specific conclusion, model disagreement/borderline explanation and practical recommendation. Raw branches, formulas and measured feature table are collapsed in advanced diagnostics.
- [x] Display risk score (higher = more risk), phishing report trust score (100 minus risk; higher = less detected risk), and qualitative assessment confidence with a reason. This display-only trust index does not change shared backend `trust_risk_score` semantics, detector decisions or other module reports. No statistical confidence percentage is fabricated.
- [x] PDF includes the same specific findings, score definitions and confidence explanation. Borderline opinions remain uncertain even just below threshold.
- [x] Added regression checks for 69.9/70 boundary, 7.6/99 branch disagreement, inverse trust calculation, missing evidence, actual redirect/form targets, certificate issuer and rendered report content. Build and regression checks passed; browser visual review remains pending.

## Evidence opinion and visual comparison — 17 October 2026

- [x] Kept uncertain verdicts while adding an explicitly qualitative opinion: phishing, suspicious, weak legitimate leaning or insufficient evidence. Strong/medium forensic findings take precedence; model threshold and observed coverage support the explanation. No fabricated confidence percentage or score change.
- [x] Added insertion/deletion-aware domain alignment with highlighted character changes, canonical positions and Unicode code points. Explains destination identity and impersonation risk without claiming that a spelling difference proves malicious intent.
- [x] Surfaced existing PhishStats exact-URL match provenance, scope, dates, report IDs, provider score, cache status and incomplete lookup warnings. Distinguished recent qualifying reports, historical reports, no match and unavailable checks. Extended PDF output.
- [x] Domain alignment/Unicode/insertion/deletion and opinion-policy regression checks passed; TypeScript, scoped lint, production build and Git whitespace checks passed. Implementation and suggested future work documented in `docs/phishing/report-evidence.md`.
- [ ] Optional next integration: PhishTank verified-online feed, subject to provider access; not connected or claimed active. Add independent exact-match corroboration and feed freshness monitoring before stronger corroborated labels.
- [ ] Browser visual review and independent confidence calibration remain outstanding; image/scam code and detector decisions unchanged.

## Phishing report presentation — 17 October 2026

- [x] Added phishing-specific color-coded verdicts, live-check coverage visualization, URL destination/path breakdown, lookalike comparison and forensic evidence cards with relevant locations and policy participation.
- [x] Added diagnostic structure/text/ensemble bars, original model label and threshold, score formula, evidence weights and observed feature table. Distinguishes model inference from recorded forensic evidence; exact character-level model attribution is not available.
- [x] Expanded PDF export with forensic findings, destinations, model diagnostics, policy weights and feature measurements. Certificate verification text now reflects the recorded verification outcome.
- [x] Detection policy, scores, image/scam implementations and shared report components remain unchanged. Low-risk verdict is qualified as likely legitimate; ownership is not claimed verified.
- [x] TypeScript and production frontend build passed; Git whitespace check passed. Browser visual review remains outstanding.
- [ ] Future model work: validated local feature attribution and independent combined-score confidence calibration. Current UI explicitly identifies both limitations.

## Phishing-only cleanup — 17 October 2026

- [x] Removed 19 obsolete phishing files (11,994,585 bytes): rejected modern-v4 binaries/trainer, two one-off debug scripts, duplicate final/progress text checkpoint, stale pre-fix reports and obsolete sign-in/verification/Colab screenshots. Exact paths are listed in `models/phishing_url/research/cleanup-2026-10-17.json`.
- [x] Removed the unused modern-v4 runtime branches, its unmasked text function, unused imports and the redundant non-resumable progress-file write. Current masked model functions and all four manifest-listed artifact hashes are preserved.
- [x] Retained current training inputs, the structural retraining dependency, referenced research experiments, current diagnostics/reports, domain-reference licenses and supported rollback/GPU workflows. Updated phishing README/model card to distinguish current runtime from historical workflows.
- [x] 71 regression tests passed after rerunning outside a Windows sandbox asyncio socket stall. Cleaned Python syntax and Git whitespace checks passed. Rebuilt only phishing services; both healthy. Deployed model/forensic checks retain Google 16.2, PayPal 20.6, PayPal lookalike 84.1 and FTP lookalike 80.0.
- [x] Image/scam/shared-app implementation and running services were not modified. Protected detector-source diff fingerprint remains `ff8528f7f63317f9ef65c2cf419742b93466ab7f`. Branch `nirmala`; no commit or push performed.

## Local launcher readiness correction — 17 October 2026

- [x] Investigated `Startup incomplete: image`: the image environment imports successfully and the already-launched image API subsequently returns HTTP 200. The 45-second full-startup deadline reported failure before cold image startup completed.
- [x] Batch launcher now uses `scripts/start-web-services.ps1` for hidden image/trust/frontend processes with persistent runtime-logs and recorded process IDs. Healthy existing processes are preserved. No image/scam detector implementation was changed.
- [x] Full startup checker now has a configurable 240-second default and progress/log guidance. PowerShell syntax and Git whitespace checks passed. Live recovery check preserved the running processes, all website service checks passed, and real scam inference/auth validation passed (SUCCESS; unauthenticated Gateway request rejected with 401).

## Link input and visual-domain correction — 17 October 2026

This section supersedes earlier HTTP/HTTPS-only input and missing visual-domain coverage. The web collector remains restricted to HTTP/HTTPS; user input handling is now separate.

- [x] Accept bare domains, host/port/path and scheme-relative links; infer HTTPS while preserving the original input and canonical hostname. Existing explicit web paths/query encoding are preserved.
- [x] Accept other URI schemes for offline destination inspection, never execute scripts/apps/files or send FTP/mailto to the web model/collector. Unsupported protocol legitimacy remains unknown rather than receiving an invented safe score.
- [x] Added generic visual-domain comparison using an updateable 10,000-domain Majestic reference and 6,712 Unicode confusable mappings plus disclosed i/l/1 font ambiguity. Provenance/license notices included. No domain verdict allowlist or PayPal-specific code exception.
- [x] Differentiate `paypal.com` from `paypaI.com` / canonical `paypai.com`, including observed navigation destinations. Preserve ordinary capitalization equivalence and avoid treating brand names in paths as destination identity.
- [x] Version new reports as `links-v1`; older saved phishing reports require rescanning. Input and report changes remain phishing-specific.
- [x] 71 targeted unit/integration tests passed; frontend TypeScript and production build passed. See `docs/phishing/link-inputs-and-lookalikes.md` for limitations and refresh instructions.
- [x] 11/11 authenticated asynchronous input regressions passed with persisted standard reports: bare/explicit PayPal 20.6 LOW, `paypaI.com` / lowercase `paypai.com` 84.1 lookalike risk, app1e 87.9, Google 16.2 LOW. FTP/mailto lookalikes received forensic-only indices; non-web inputs without strong evidence stayed unknown, never falsely safe. Evidence: `models/phishing_url/research/link_input_regression.json`.
- [x] Started the existing stopped Kafka/Mongo containers required by phishing; data preserved. Deployed only phishing services. Main UI backend on 8002 was not running; isolated authenticated test servers verified the new request schema and persisted results. Protected scam detector source diff remains unchanged; image detector source untouched.
- [x] Final worker ready=true; worker and collector healthy. Deployed forensic/input/policy/reference hashes match workspace. Worker image `sha256:3d0315c71ba5adfac3c3a959aa4258f4103ea34756724befcb1d7c138d5b5c46`; collector `sha256:008b33f0426f7f9eb9178427e367fcafeef5dfd671c8e9097634d8fafbfafec4`. No visual-collision warnings appeared on the 19 existing official-homepage challenges; this is a regression check, not a new accuracy benchmark.
- [ ] Independent evaluation of visual collision precision and the heuristic weight/rank threshold; broader brand/typo coverage and ownership corroboration. A popular-domain ranking is not a benign-site certificate. Prior documentation-path false positive and overall model recall limitations remain.

## Current dynamic implementation and audit — 16 October 2026

This is the current status. Earlier sections below describe historical deployments and are superseded where they conflict.

- [x] Audited v1 HTTPS data imbalance, model false positives, disabled collection, constant forensic scoring and repeated technical output. Findings: `docs/phishing/audit-2026-10-16.md`.
- [x] Replaced the default BERT/v1 runtime with CPU `modern-v5`: masked registered-domain URL text, scheme-neutral structure, learned fusion and separate calibration. No runtime brand/domain allowlist. Candidate artifacts are separate and hash checked.
- [x] Included representative HTTPS data; domain-disjoint source partitions. Source test precision 96.33%, recall 70.85%, F1 81.65%, false-positive rate 0.964%. Evaluation was reused during development; these are not independent production accuracy claims.
- [x] Rejected structure-only and unmasked-text candidates after evaluation. Retained their reports for audit.
- [x] Enabled isolated authenticated live DNS/TLS/redirect/static-page/password-form/RDAP/reputation collection by default. Public-address checks, verified TLS, deadlines and bounded pages remain enforced. Collection does not execute JavaScript or submit credentials.
- [x] Added fresh exact-URL PhishStats evidence, indexed hostname-only queries, generic batch prefetch, persistent 90-minute cache, daily request budget and provider backoff. Input labels are never inserted as reputation records. No match/outage/quota is never treated as safe.
- [x] Replaced blanket HTTPS UNAVAILABLE and constant 75-point results with `dynamic-v2`. Supported model results retain numerical shared trust scores when some network checks are unavailable. Combined score is a disclosed risk index, not a probability.
- [x] Simplified phishing summary and PDF report: one verdict, standard trust score, plain reasons, actual destination, individual live-check states and expandable technical details. Old saved reports require a new scan.
- [x] 62 targeted unit/integration tests passed, including certificate parsing/failures, redirect hops, encoded navigation, IPv4 fallback after AAAA timeout, reputation batching, SSRF/TLS boundaries, dynamic evidence, score persistence, replay and ownership. Frontend TypeScript and production build passed after the certificate/navigation UI extension.
- [x] Added TLS certificate signature/hash/public-key analysis and fingerprints after verified handshakes, explicit validation-failure evidence without insecure retry, intermediate downgrade/domain-hop checks and local encoded-path/navigation-parameter inspection. Certificate trust does not imply site safety; revocation is not checked. Findings and hop details are included in phishing UI/PDF.
- [x] All four live certificate/navigation controls passed: Google valid TLS; GitHub redirect; expired and mismatched badssl certificates. Fixed default-port Host header handling that broke scheme-changing redirects, and retained partial hops on later failures. Evidence: `certificate_navigation_live.json`.
- [x] Final authenticated asynchronous Gateway/Kafka/deployed worker/Mongo/isolated SQLite smoke passed: 401/403 ownership, invalid scheme rejection, shared score equality, and saved Google 16.2 LOW with actual certificate/navigation evidence. Evidence: `platform_verification.json`. Only phishing services were rebuilt/recreated; shared Kafka/Mongo were not restarted.
- [x] Final deployment check: worker ready=true; worker and collector healthy. Worker image `sha256:3d58e1b675165b7d00ccd4b9cd0f58b90086fef01aa5174655e00d068af7397c`; collector image `sha256:4b93cc6b92fd3ce6c583ed9ee398da5c07aa31b5569291d61e271eb3230f7a80`. Deployed collector safe_fetch SHA256 matches workspace: `9db4f1aa97cc3ebd30feffeb653bdfcdc18e33b7d83a7e8552b1b0cb67ba83e9`.
- [x] Authenticated asynchronous Gateway/Kafka/worker/persistence tests cover mixed source-labelled URLs and four legitimate paths. Full observations and external-comparison access states are recorded in `dynamic_url_audit.json` and `dynamic_url_paths.json`.
- [x] Final mixed sample: 0/8 official-homepage alerts; model-only 5/8 reported-phishing alerts; current-evidence policy 8/8. Supplementary paths: 1 false alert, 1 review, 2 low. Positive references and reputation share PhishStats, so the 8/8 result is not independent accuracy.
- [ ] **Known false positive remains:** `https://docs.python.org/3/` scored 93.7 in the path audit, driven by the learned URL model (structural 0.690, text 0.939), with no corroborating forensic finding. GitHub's `/openai` path scored 30.6/review. Do not claim arbitrary legitimate paths are fixed or hardcode exceptions. Add a broader independently labelled path/subdomain corpus and retrain/re-evaluate.
- [ ] Improve model recall: source-only model misses about 29% of labelled phishing URLs at the selected threshold. Fresh reputation addresses some observed misses but does not solve unseen-campaign recall.
- [ ] Independently validate/calibrate the full evidence index and its manually configured generic weights; collect a fresh temporal holdout. Text SGD reached its 25-iteration cap; convergence needs further evaluation.
- [ ] Broader independent provider comparison: urlscan returned access errors/no exact reports; VirusTotal authenticated access unavailable. Same-provider PhishStats sample plus reputation is not independent accuracy or evidence of superiority.
- [ ] JavaScript/cloaking inspection and broader production validation remain outside the current static-page collector. Anonymous reputation quota can be exhausted; cached results and URL analysis continue with explicit coverage.

Only phishing-specific code/UI/deployment was changed for this audit. Existing image/scam detector edits were preserved. Branch remains `nirmala`; no commit or push was performed. The broken host `.venv` is not repaired by this work; the deployed phishing worker uses its Docker CPU runtime.

## Current forensic implementation — 16 October 2026

This section supersedes older branch-only/confidence-only safeguards below.

- [x] Offline URL forensic rules: true destination/userinfo deception, offline public/private suffix boundaries, IP/non-public destinations, IDN/mixed-script labels, selected hostname impersonation/lookalikes, unusual ports, HTTP and encoding.
- [x] Forensics runs without model output and after model inference failure; weak indicators require review and are never summed into proof.
- [x] Protected optional collector observations now affect the policy: RDAP age on registered domain, DNS/TLS availability, final redirect destination/downgrade, static password-form actions, HTML base URL and explicit form ownership. No JavaScript execution or credential submission.
- [x] Empty root path normalisation fixes slash/no-slash feature discrepancies; submitted URL preserved and inference policy versioned as forensics-v1.
- [x] Unsupported v1 HTTPS probabilities, conflicting branches, forensic review and uncorroborated positive predictions withhold numerical trust scores. Google HTTPS variants no longer publish 100% phishing from model output alone.
- [x] Strong forensic findings use a disclosed, uncalibrated 75/100 ordinal severity index (native anomaly score), not a phishing probability. Confidence unavailable; raw model probability retained only as diagnostic data.
- [x] Phishing UI/PDF include forensic findings, actual hostname/domain, collection coverage, plain reasons and score basis. Old hybrid/baseline v1 policy reports require rescanning.
- [x] Optional compose.forensics.yml and phishing launcher -Forensics option wire a separately networked authenticated collector; offline checks always run.
- [x] 36 targeted tests passed, including persisted null trust scores, replay identity, malformed IDNs and evidence reapplication. Final TypeScript check and frontend production build passed. Fragment preservation correction separately verified by all 18 forensic tests and deployed-code inspection.
- [x] Live authenticated Gateway/Kafka/Mongo regression: 8 URL cases, 5 invalid inputs rejected; all four Google HTTPS variants uncertain with null trust scores, deceptive userinfo URL scored as explicitly uncalibrated forensic severity. Evidence: models/phishing_url/research/forensics_regression.json and .md. No submitted websites fetched.
- [x] Final deployed worker ready=true; forensic source SHA256 matches workspace (d2c9695b9803fc3fe57dacbb0fc9d7cbc38f2b1fd8618401d43f5a8c0aec76a5). Image sha256:4c37e48720377420ffbc0f107b19b56867498359fcbc88d545cdb06642251495. Final authenticated async platform smoke passed, including 401/403 ownership checks and matching persisted forensic trust score. Other services were not restarted.
- [ ] Optional live collector activation and deployed host-gateway/egress verification: currently disabled; offline forensic checks active. Collector parsing, service integration and SSRF/TLS controls tested with controlled observations; Compose configuration validation passed. See docs/phishing/forensics.md.
- [ ] Independent labelled evaluation/calibration of rule precision and combined decision policy. Existing source F1 is not accuracy for this new policy.
- [ ] Representative HTTPS retraining, broader impersonation/reputation coverage, JavaScript-rendered inspection and production egress/security validation.

No image or scam-message detector source was edited for this forensic implementation. Previously existing changes in those files are preserved.

## Kaggle preparation — 14 October 2026

Added Phishing_Kaggle.ipynb and kaggle_run.md. BERT training now saves atomic resumable model/optimizer/RNG state every 500 batches and at epoch boundaries, rejects changed dataset/configuration on resume, uses deterministic per-epoch ordering and prints training percentage/progress.json. Percentage excludes validation and test work. Checkpoint restore has a numerical next-update equivalence test. The refreshed GPU ZIP includes the Kaggle notebook/guide. Old Colab weights without resume.pt cannot resume the interrupted optimizer/batch state. Kaggle outputs must be saved/downloaded and attached to a later session; /kaggle/working alone is not permanent. Kaggle account sign-in/GPU verification and actual remote training remain pending.

Checkpoint numerical equivalence test passed after an approved rerun: the Windows sandbox blocked atomic file replacement in its temp directory. Notebook code syntax checks passed. Browser opened Kaggle's sign-in page; user authentication is required before private dataset/notebook setup. No Kaggle upload or training run has completed yet.

## Colab run — 13 October 2026

Continuation check: the same cell remains executing on T4 (6m27s observed), GPU memory 2.4/15.0 GB. No cell output/error or completed epoch has been observed. Colab's resource panel estimates up to 4h10m for the current free session; this is not guaranteed. The run was left intact and the notebook preserved for follow-up. No training metrics or successful completion is claimed.

Opened the existing user notebook `https://colab.research.google.com/drive/1b59gie5al5t29RPGhdltRrm9imfmQOjm`. Live diagnostics confirmed Tesla T4/CUDA, mounted Drive, extracted package and the Python environment. Corrected notebook root/checkpoint paths and enabled streaming training output. Requested the full three-epoch BERT run (batch size 8); the training cell is executing but first batch progress has not yet been observed. Post-training fusion/evaluation and result-export cells have been requested afterward. Outputs target `My Drive/TrustNetPhishing/checkpoints`. No completed training, hybrid evaluation or promotion is claimed yet.

Updated 12 October 2026. Scope: phishing plus its additive Gateway/scan/UI/deployment integration. Scam-message working-tree edits were already present and have been preserved. Image detection source has not been edited.

13 October 2026: Added `docs/phishing/Phishing_Colab.ipynb` for remote GPU training using the existing ZIP. Notebook preserves Colab's CUDA PyTorch, verifies package files, stores generated checkpoints in Drive and exports the trained bundle/metrics. Code cells syntax-checked locally; actual Colab/GPU execution remains pending. Trainer has epoch-end best-model saving but no mid-epoch optimizer resume; free-session completion is not guaranteed.

The RF baseline now works through the deployed worker and authenticated Gateway path. The complete plan is **not yet an achieved research/deployment milestone**: the user selected preparing the full BERT run for a GPU machine, so full hybrid training/evaluation remains external work. Code/pipelines and measured results are distinguished below.

| Phase | Implemented / verified | Remaining gate |
|---|---|---|
| 0 Research/requirements | requirements, inventory, release hashes, cleaning policy, research comparison; approved Kaggle v1 labels/license metadata | Authoritative UCI target dictionary, freshness snapshot labels/terms, full BGL methodological review; primary original collection lineage is unavailable |
| 1 Architecture/contracts | canonical phishing topics/events, same scan ID, existing BaseDetector/DetectionResult, queued lifecycle; additive URL completion subscription and mapping | Production infrastructure/retention agreement; no shared detector enum changes |
| 2 Scaffolding | model/service packages, frozen feature schema, pinned BERT revision, local dependency lock, GPU script/package, health/readiness | Validate CUDA dependency compatibility on GPU destination |
| 3 Backend/metadata | URL intake validation, authenticated ownership, pinned-address fetch, private/mapped-address rejection, TLS verification, redirects/body/DNS bounds, isolated optional collector with process deadline | Optional collector deployment/network policy and metadata parity. Observations are NOT trained metadata features |
| 4 Models | UCI LR/RF conditional-label experiment, full primary LR/RF training/test, full LightGBM training, BERT loading/backward verification; full BERT/fusion/calibration/fallback/bundle/test scripts | Execute prepared full GPU BERT run, measured hybrid/component ablations, primary ten trained folds, freshness/robustness/grouped uncertainty, enriched configuration |
| 5 Integration | Mongo durable completion ledger, Kafka manual commits/replay, URL scan persistence/Trust Engine fusion, real Gateway polling UI, phishing report/PDF; real broker and authenticated platform smoke tests | Final hybrid promotion and PostgreSQL deployment verification; smoke uses isolated SQLite |
| 6 Testing | 84 regression tests + 12 subtests; 20 focused image analyzer tests; frontend build; real duplicate replay and owner isolation; measured baseline latency | Final hybrid security/reliability/performance slices; broad external-provider image suite was interrupted after partial progress and is not claimed complete |
| 7 Deployment | Final non-root read-only baseline image rebuilt/recreated; readiness true and latest URL validation verified. Compose baseline/hybrid/collector configs, S3/MinIO checked transport, rollback guide, reference Kubernetes manifest | Actual MinIO publication/download, hybrid/Kubernetes rollout and rollback exercise |
| 8 Documentation/demo | model card, GPU run guide/package, acceptance checklist, deployment and demo instructions | Return actual GPU/freshness/production evidence and update promotion decision |

## Measured models

| Model | Dataset/input | Test F1 | Test recall | Test ROC-AUC |
|---|---|---:|---:|---:|
| LR | Primary lexical | 0.5321 | 0.3967 | 0.7387 |
| RF | Primary lexical | 0.6670 | 0.5743 | 0.8766 |
| LR | UCI features, conditional mapping | 0.9471 | 0.9391 | 0.9854 |
| RF | UCI features, conditional mapping | 0.9695 | 0.9679 | 0.9963 |

RF still misses about 43% of the held-out phishing examples at its validation-selected threshold. These measurements must not be marketed as complete phishing protection. LightGBM final configuration uses selection-validation domains only for early stopping; full validation ROC-AUC is 0.8882. Its untouched test is reserved for frozen hybrid evaluation. UCI feature experiments are not deployable URL models and cannot be compared directly with lexical metrics.

RF runtime: 50 held-out URL samples; cold load 6375 ms, warm p50 62.5 ms/p95 79 ms. No DNS/WHOIS/TLS/HTML collection included. CPU source BERT load/classification forward/backward verified, but no BERT phishing accuracy is claimed.

## Data and leakage controls

Approved primary taruntiwarihp/phishing-site-urls v1: original good=392,924 / bad=156,422. good→0 legitimate, bad→1 phishing, verified by official uploader description. 549,346 source rows → 500,085 retained; 9,002 invalid URLs, 312 unknown suffixes, 39,944 duplicates and 3 conflicting-label rows excluded. Train 360,066 / validation 40,006 / held-out test 100,013; zero domain/fold overlap and both labels in each of ten development folds. Fixed PSL/private suffixes and source/prepared/metadata/split hashes recorded.

499,978 retained URLs lack a scheme. Original input and scheme_inferred flag are preserved; assumed HTTP is parsing provenance, not observed transport. Dates/campaign families/original collection lineage are unavailable. Current collector observations cannot replace historical training metadata.

UCI archive: 11,055 original rows, 5,206 duplicate rows, 64 conflicting feature vectors; experiment retained 5,721 unique unambiguous vectors. Ten-fold development and frozen feature-disjoint test recorded. Experiment uses explicit -1=phishing/+1=legitimate with conditional interpretation; official supplied metadata does not define target direction and published conventions conflict.

## Training and operation

Local baseline: `./scripts/start-phishing.ps1 -Kafka` (trained rf.json by default). Infrastructure: Kafka localhost:9094, Mongo localhost:27017. Existing Gateway/Scan Management must have Kafka enabled. Browser requests use Gateway only.

Compose baseline: `docker compose -f docker-compose.yml -f services/phishing_url/compose.phishing.yml up -d --build phishing`. Collector is opt-in and separate; hybrid override is used only after evaluated GPU bundle promotion.

GPU package: `exports/phishing-gpu.zip` (~424.5 MB), digest in `models/phishing_url/research/gpu_package.json`. Includes complete frozen data, pinned pretrained BERT source, trained LightGBM and training/fusion/evaluation code. Follow `docs/phishing/gpu_run.md`; run `bash scripts/train-phishing-gpu.sh` on CUDA hardware. Return hybrid bundle + hybrid_test.json. No external GPU job has been submitted or executed from this chat.

Model selection/voting uses validation domains with SHA256 mod3=0; calibration uses mod3=1; threshold uses mod3=2. The test set is never used for selection. Single-branch fallback calibration/thresholds are separately fitted on these validation partitions. Runtime never loads training CSVs or fabricates scores when artifacts are unavailable.

## Verification evidence

## UI activation and implementation checklist

The existing scanner's **Phishing Websites** tab now renders PhishingScanView instead of the unavailable placeholder. Launchers bring up the phishing Docker worker/Kafka/Mongo and enable Kafka for Scan Management when infrastructure succeeds. Restart existing Scan Management processes to pick up that setting. Image/scam detector source is untouched.

UI activation verification: `npm run build` passed with PhishingScanView included in ScanUploadView. PowerShell launcher syntax parsing and `git diff --check` passed. Branch remains nirmala. GPU package refreshed with step-by-step installation, CUDA verification, training and artifact-return instructions.

Done:
- [x] Phishing tab connected in the existing scanner.
- [x] Real authenticated Gateway submission, polling and matching scan IDs.
- [x] Processing, failed/unavailable and partial-result states.
- [x] Phishing report view and PDF export; no image verdicts.
- [x] Trained lexical LR/RF and LightGBM branch, checked artifacts.
- [x] Mongo persistence, Kafka replay, scan completion and ownership checks.
- [x] Docker worker, startup integration and health/readiness.
- [x] GPU training/fusion/calibration/evaluation package and instructions.
- [x] Baseline model card, phase tracking and regression evidence.

Remaining:
- [ ] Execute full BERT training on the selected GPU machine.
- [ ] Freeze/evaluate/promote the trained LightGBM+BERT hybrid and fallbacks.
- [ ] Train all ten primary development folds and report variation.
- [ ] Freshness/robustness/domain-bootstrap evaluation.
- [ ] Verified historical metadata configuration and enriched model training.
- [ ] Resolve authoritative UCI labels and complete reference-paper review.
- [ ] Production PostgreSQL/MinIO, hybrid deployment and rollback verification.
- [ ] Kubernetes rollout; GNN remains a later upgrade.

This checklist does not claim the complete hybrid plan is finished.

- `models/phishing_url/research/primary_preparation.json`, `primary_models.json`, `uci_baselines.json`, `baseline_latency.json`.
- `live_worker_verification.json`: real Kafka/Mongo, durable duplicate event identity.
- `platform_verification.json`: real signed JWT Gateway → Scan Management → Kafka → deployed worker → persisted result/trust; missing auth/invalid scheme rejected, another user denied. Isolated SQLite relational store, not production PostgreSQL.
- `pytest models/phishing_url/tests services/phishing_url/tests services/scan_management/tests services/trust_engine/tests shared/tests gateway/tests -q`: **84 passed, 12 subtests passed** after final validation changes.
- Focused image preprocessing/metadata/watermark/recompression tests: **20 passed**. Protected source was not changed.
- `npm run build`: passed with phishing report/real UI.
- Final Docker build/recreate and `/ready`: passed, including S3 dependencies and required-URL validation. Image digest `sha256:c8c5d6d706202f0715784ce771c9e9d3252c043d3f5054ac5da6648d20ba5c7b`. Existing Kafka/Mongo containers remain running with the phishing worker on loopback port 8007.

Sandbox blocked Windows asyncio's internal socketpair and stalled early async runs. Diagnostics identified socket.accept in event-loop startup; those runs were interrupted and approved reruns passed. This was not classified as a detector failure.

Remaining acceptance gates and limitations are in `docs/phishing/acceptance.md`. GNN remains the plan's later upgrade. Do not mark the full plan complete before measured GPU/hybrid/freshness/production gates are fulfilled.

## Kaggle setup - 14 October 2026
- [x] Imported and saved TrustNet Phishing GPU Training notebook on Kaggle.
- [x] Uploaded refreshed 424.51 MB GPU ZIP with Private visibility; dataset creation submitted and processing observed.
- [ ] Confirm dataset processing finished and attach the package dataset (the notebook briefly attached its own empty output; remove that input before running).
- [ ] Complete user phone verification: Kaggle currently disables GPU T4 x2 and internet until verified. Account shows 30 GPU hours available, 0 used.
- [ ] Enable GPU/internet, run setup, full BERT training, fusion and held-out evaluation.
Training has not started on Kaggle. Verification dialog is open for the user; phone entry, CAPTCHA and SMS verification require user action.

## Kaggle training launched - 14 October 2026
- [x] User completed verification; GPU T4 x2 and internet enabled.
- [x] Private package dataset processing succeeded (82 extracted files); attached correct dataset and removed empty self-notebook output.
- [x] Saved private notebook Version 1, full training commit launched: https://www.kaggle.com/code/nirmalapatole/trustnet-phishing-gpu-training?scriptVersionId=358338595
- [x] Setup passed package verification/dependency install/CUDA check. Logs confirm BERT loaded, training_ready with 360066 rows, 45009 steps per epoch, fresh run, epoch 1 step 1 completed with loss 0.7799385786056519.
- [ ] Await full training, validation, fusion, held-out evaluation and output archive. The run is active, not complete; progress percentage counts training batches only.
Evidence screenshot: models/phishing_url/research/kaggle-training-started.png. Saved Kaggle commit runs independently of this browser; checkpoints are written every 500 steps and epoch boundaries.

## Returned GPU artifacts - 15 October 2026
- [x] Received results.zip containing completed Kaggle output and nested deployment ZIP.
- [x] Imported only hybrid/BERT/fusion artifacts and training/evaluation evidence; source code and protected modules were not imported.
- [x] Verified eight hybrid artifact hashes, frozen prepared-data hash and three epochs/full training partition.
- [x] Recorded held-out test results and branch tradeoffs in docs/phishing/model_card.md: hybrid F1 0.93771, recall 0.92384, precision 0.95200, FPR 0.01278 on 100013 rows.
- [ ] Promote the verified hybrid into the running worker and check API/UI, rollback and local latency.
- [ ] Remaining ten-fold, freshness/robustness, enriched metadata and production gates still apply.
- [ ] Local Windows hybrid inference smoke remains unverified: both sandboxed and approved outside-sandbox loads stalled before returning a prediction and were interrupted. No live worker promotion performed. Kaggle held-out evaluation completed; artifact/hash verification passed locally.

## Hybrid integration - 15 October 2026
- [x] Local hybrid load and prediction passed; both LightGBM and BERT APPLIED, calibrated score and TreeSHAP evidence returned. Earlier stalled runs were superseded by this successful run. Windows Transformers import scans installed module files and can be slow on first load.
- [x] Host phishing launcher defaults to hybrid/manifest.json.
- [x] Existing development infrastructure launcher selects hybrid Compose override; explicit -Baseline rollback preserved.
- [x] Hybrid container installs pinned CPU-only torch 2.6.0+cpu, Transformers 5.19.0 and safetensors 0.8.0; CUDA is not required for inference.
- [x] Regression: 78 passed, 12 subtests passed outside sandbox. Sandbox run interrupted after restricted atomic checkpoint/asyncio operations.
- [ ] Hybrid container readiness and authenticated end-to-end scan verification in progress.

## Current implementation checklist - 15 October 2026 (supersedes earlier pending GPU/local-promotion entries)
- [x] Prepared frozen domain-separated dataset and trained LR/RF, LightGBM and full three-epoch BERT.
- [x] Validation-only fusion, isotonic calibration, thresholds and single-branch fallbacks; held-out test evaluation imported.
- [x] Checked hybrid artifact and dataset hashes; local inference passes.
- [x] CPU-only Docker hybrid runtime fixed: torch 2.14.1+cpu, Transformers 5.19.0, safetensors 0.8.0. Torch 2.6 CPU accelerator detection failed and was replaced; final build verifies imports.
- [x] Hybrid worker deployed on 127.0.0.1:8007, readiness true. Final image digest sha256:703362edc1c399423044b4a7868e311cae5d23dc1acafc835e6640c91ed60f8d.
- [x] Default host/infrastructure launchers select hybrid; explicit baseline rollback option documented.
- [x] Authenticated Gateway -> Scan Management -> Kafka -> hybrid worker -> Mongo -> persisted report and trust result verified, hybrid-v1 and both branches APPLIED. Invalid URL/auth and owner isolation checks pass. Isolated SQLite relational test store; no production PostgreSQL claim.
- [x] Existing phishing UI submit/poll/report/PDF path remains connected; frontend production build passed.
- [x] Regression suites: 78 tests + 12 subtests, plus 7 trust tests = 85 tests + 12 subtests passed.
- [x] Work remains on nirmala; no scam-message or image module source edits made in this continuation.
- [ ] Representative warm/cold latency distribution, throughput and robustness/domain-bootstrap checks.
- [ ] Freshness/temporal evaluation, ten trained development folds, historical-metadata parity, authoritative UCI label resolution/reference-paper review.
- [ ] Production PostgreSQL/MinIO/Kubernetes validation and an exercised rollback drill. Rollback command is implemented; drill not claimed complete.
- [ ] GNN upgrade remains later scope in the plan.
Use the existing start-dev launcher, then Scan -> Phishing, enter an HTTP(S) URL, Analyze and open the phishing report. Docker Desktop must be running. No local CUDA required. First-load imports and first inference can take longer than warmed requests.

## Launcher error fix - 15 October 2026
- [x] Windows PowerShell Docker stderr warning no longer terminates phishing startup; Docker failures still follow actual nonzero exit status.
- [x] Model readiness timeout increased from 45 to 240 seconds with periodic pending-service notices; health/readiness checks remain required.
- [x] Added explicit -PhishingKafka launcher option, passed by start-dev.bat after successful phishing startup; only Scan Management inherits Kafka enabled. Scam/auth/gateway retain their existing synchronous setting.
- [x] Verified phishing infrastructure launcher under Windows PowerShell and backend startup with -PhishingKafka: scam model completed loading, all readiness checks passed, Scan Management Kafka producer initialized.
- [x] PowerShell syntax checks passed. No scam-message or image module source/artifacts changed. Verification-owned backend processes stopped afterward for a clean full-launch retry.

## Standard result format and varied URL testing - 15 October 2026
- [x] Phishing results now use the shared verdict/explanation contract and structured presentation: verdict, risk /100, confidence availability, branch estimates, evidence, analysis layers, assessment dimensions, limitations and next steps.
- [x] Phishing report and PDF contain matching sections; scan summary uses the same verdict/explanation/confidence semantics. Message/image source and shared result schema were not changed.
- [x] Reproducible authenticated Gateway/Kafka/Mongo suite: 25 varied URL inputs (10 public addresses, 10 seeded synthetic URLs, 5 edge cases) and 5 malformed/non-HTTP inputs; initial pass completed, final coverage-aware run in progress.
- [x] Found HTTPS training skew: 0 legitimate HTTPS and 6 phishing HTTPS training rows; test contains only 1 HTTPS row. Familiar homepages received high model risk. Source benchmark scores are not evidence of live HTTPS reliability.
- [x] HTTPS confidence is withheld for current v1 artifacts and explicit outside-validated-coverage/experimental notices appear in API/UI/PDF. Raw model scores remain unchanged; no allowlist or threshold override added.
- [x] Final regressions: 89 tests + 12 subtests passed. Frontend production build passed.
- [ ] Representative HTTPS data, corrected/versioned training and independent validation/calibration are required to resolve the observed live-URL reliability concern.
- [x] Final coverage-aware URL suite completed: all 25 valid cases returned matching persisted shared-schema results; all 5 invalid inputs rejected (HTTP 422). All HTTPS cases confirmed outside-validated-coverage status and withheld confidence. Results: models/phishing_url/research/url_suite.md and url_suite.json. No URLs fetched. This is functional testing without verified ground-truth labels, not an accuracy benchmark.
- [x] Final presentation/coverage update deployed to local hybrid worker; final image sha256:dcc95db17f811797a189432413a8aa60cc3b946dfc7645e1d257690602f73f76. Existing historical scans retain their original stored payloads; rescan for current coverage fields.

## Trust score, reasons and accuracy remediation - 15 October 2026
- [x] Phishing report now uses the shared TrustScoreGauge and persisted trust-engine risk score. Higher means greater risk, matching existing modules; it is not inverted into a safety guarantee.
- [x] Normal-language reasons reflect observed destination/userinfo/IP details and measured model feature contributions. Report and PDF include reasons, evidence, analysis layers and limitations.
- [x] History formatting handles phishing separately from image manipulation wording. Legacy hybrid scans without the current policy marker display rescan required and withhold old scores.
- [x] Diagnosed BERT live errors beyond HTTPS skew: HTTP Google is also misclassified; fixed vs dynamic token padding produces matching scores, ruling out a padding mismatch.
- [x] Existing calibrated branch thresholds now require agreement for a conclusive assessment. Disagreement produces UNCERTAIN/UNAVAILABLE and no fused trust score; original probabilities are diagnostics, not a successful phishing verdict.
- [x] Measured reused-validation diagnostics: 84.4% assessment coverage; 99/116 prior false-positive alerts withheld. Not an independent accuracy benchmark.
- [x] End-to-end focused regression: Google with/without www and Wikipedia uncertain with null trust score; GitHub 1/100 risk; synthetic account path high risk. All five malformed inputs rejected. accuracy_regression.json/md.
- [x] Final regression suite before optional candidate work: 90 tests + 12 subtests passed; frontend build passed. Additional URL-text representation/presentation checks: 8 passed.
- [x] Isolated test completion consumer groups prevent competing with the running application's Kafka completion consumer.
- [x] Downloaded official CC BY 4.0 UCI PhiUSIIL and trained a separate scheme-neutral CPU candidate, excluding challenge domains from train/calibration, zero domain overlap, 45 conflicting canonical URLs removed. Source dataset URLs were never visited.
- [x] Candidate rejected for promotion: test F1 0.8178, recall 0.6985, GitHub challenge false positive. Default startup remains on the hybrid agreement safeguard; candidate artifacts preserved separately, not deployed.
- [ ] Underlying BERT/live accuracy is not fully resolved. Representative retraining plus independent labelled deployment evaluation remains required; no safe-domain allowlist or fabricated score overrides were added.
- [x] Work on nirmala; no scam-message or image module source changed in this task. Refresh the UI and submit a new scan; old scan IDs retain their original immutable stored assessments.
- [x] Final post-candidate regression: 93 passed, 12 subtests passed. Active worker /ready true. Focused live results confirm branch-agreement-v1 policy marker on all five URL cases and null trust scores for both Google variants/Wikipedia.
- [x] Active deployed hybrid image sha256:fd4f3d5f90f5d4e00da1102767197ad4bec5812f1f9fb6fa3cb635ed797a42a5. Optional URL-text candidate remains rejected and is not a default launcher target.
