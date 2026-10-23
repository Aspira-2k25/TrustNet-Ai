# Image detection remediation: pretrained Hugging Face integration

Date: 23 October 2026. Status: implementation plan only. Preserve the original TrustNet UI and all unrelated modules. No model inference, external image upload, token validation, training, or policy activation was performed for this plan.

## Evidence and current state

- The supplied hovercar report, scan-586738cd37, reports REVIEW REQUIRED and a 55.5/100 index. Its explanation says no validated operating point is installed.
- Local reproduction on the supplied 1672×941 PNG returns one Haar face proposal at [842,714,194,194], over non-face scene content. That incorrect proposal admits the image to the face-classification path.
- Metadata analysis finds an unverified Chatgpt string in an embedded binary chunk. It is not authenticated provenance and must not be converted into a classifier probability.
- The configured model is dima806/deepfake_vs_real_image_detection. Its model card links to a face-detection training notebook and warns of concept drift from older training data. Do not assume its published benchmark applies to contemporary scenery, objects or generated art.
- HUGGINGFACE_API_KEY is present in .env; its value was not displayed or sent anywhere. Token validity, inference permission, billing and provider availability remain unverified.
- IMAGE_ASSESSMENT_POLICY is absent in .env and defaults in code to image-vit-v3. That policy calls local_vit.predict/predict_views directly. A configured key does not activate the hosted client.
- IMAGE_ALLOW_HOSTED_INFERENCE is absent and defaults to false. The existing HuggingFaceDeepfakeClient has a hosted route, but it is not the active v3 prediction path. A second general model is explicitly rejected by both existing clients.
- The restored original PDF exporter substitutes a success-sounding sentence for missing findings, including skipped analyzers. It also labels a scan-ID/time string as SHA256 and prints a certification claim. These are reporting defects independent of classifier accuracy.

## Scope and boundaries

Use pretrained Hugging Face models. No CNN training is required for this implementation. Keep the current face model as a specialist/baseline while assessing a pretrained general-image AI detector. Model selection is a release gate; this plan does not name an unverified model or promise that API access will correctly classify the hovercar.

Preserve the original navy/cyan layout, navigation, cards and controls. Change only assessment behaviour, evidence fields, necessary status wording and accurate export contents. Preserve authentication, upload limits, existing image-retention rules and unrelated phishing/message behaviour.

## Phase 1 — Freeze baseline and reproduce

1. Save baseline API responses, model identity, processor hash, active mode, face boxes and timings for the hovercar and earlier portrait. Keep source images local under existing retention rules; do not commit private images.
2. Add regression expectations for the supplied crop: it must not be accepted as a verified face by the replacement localizer. Do not assert a predetermined AI score for this single image.
3. Record the original UI and response contract. Establish a feature-flag rollback to current image-vit-v3 without resetting backend work.

Gate: deterministic reproduction of the invalid face proposal and the current review-required path. Existing image tests pass before changes.

## Phase 2 — Explicit Hugging Face backend and model contracts

Primary files: inference/huggingface_client.py, inference/local_vit_detector.py, inference/classifier_contract.py, inference/efficientnet_detector.py, service readiness/configuration and .env.example.

1. Introduce explicit local/hosted backend selection and separate general/face model identities in an image configuration object. Proposed names: IMAGE_INFERENCE_BACKEND, HF_GENERAL_IMAGE_MODEL and HF_GENERAL_IMAGE_REVISION. Retain HUGGINGFACE_API_KEY server-side. These names are proposed additions, not existing settings that already work.
2. Use the documented Hugging Face image-classification interface. Verify task support, provider availability, permissions, model license, input limits, label meanings and complete response shape before admitting a model to the registry.
3. Each registered model declares its label mapping, scope, processor, revision/deployment identity and score definition. Unknown/duplicate labels, incomplete distributions, invalid ranges, malformed payloads and empty predictions fail closed. Never substitute 50 or zero as an applied prediction.
4. Record requested and actual model/provider/backend, deployment identity, preprocessing, latency and fallback reason. An unpinned hosted deployment is explicitly marked; it must not reuse a policy validated for a pinned local artifact without equivalence evidence.
5. Implement bounded timeouts, concurrency, image encoding/size budgets and selective retry/backoff for retryable errors. Treat 401/403, billing/402, 429, 5xx and schema errors distinctly. Do not call whoami or inference synchronously during construction/readiness probes.
6. Local fallback is explicit and optional, with matching model/preprocessing identity and reported execution mode. Never silently switch to a different face-only model to satisfy a general-image request. Invalid responses must not become successful fallback scores.
7. Readiness reports credential presence, configured backend, scope capabilities and cached load/connectivity state without exposing secrets. Repeated health checks must not upload images, incur inference costs or pretend that token presence proves service availability.
8. Before hosted activation, disclose that image bytes leave the machine and identify the provider. Integration tests use approved non-private fixtures; do not automatically send the user's portrait or hovercar to an external endpoint. No secret values or raw provider error bodies enter user reports/logs.

Gate: contract tests for success, provider/auth failures, malformed labels, missing keys and explicit fallback. A controlled hosted test must prove the actual execution mode and deployment identity before API operation is called verified.

## Phase 3 — Validate face localization

Primary files: forensics/face_analyzer.py and evaluation/localization.py.

1. Replace permissive multi-cascade/rotation proposals as the acceptance authority with a pretrained face detector with confidence and landmark outputs, after checking its license and runtime compatibility. Haar may remain a diagnostic proposal source, never an automatic acceptance fallback.
2. Validate bounds, dimensions, detector confidence, landmark plausibility and duplicate overlap. Detector/landmark confidence is evidence, not proof of a face. Do not use skin colour or object category alone as an exclusion rule.
3. Test buildings, windows, wheels, headlights, clouds, logos, textures and generated vehicles as hard negatives. Include real and generated portraits, profiles, occlusion, low light, glasses, varied skin tones, small faces and groups for recall.
4. Record accepted/rejected proposals and reasons. Unsupported, no face and localization unavailable remain distinct.
5. Version the detector/crop policy and invalidate incompatible operating points. A detector replacement changes score distributions; old face thresholds cannot be carried forward silently.

Gate: the reproduced hovercar building box is rejected. Review false positives and face recall on an independent annotated set, with release budgets fixed before final-test inspection. One corrected image alone is not a successful localization benchmark.

## Phase 4 — Add general-image assessment and scope routing

1. Shortlist pretrained detectors whose documented training/evaluation covers whole-image synthetic content, not only manipulated human faces. Check contemporary generator diversity, photographic negatives, CGI/artwork distinctions, license and actual hosted/local availability. Benchmark candidates before choosing one.
2. Run the selected general-image branch on supported full images independently of whether a face is found. Run the face specialist only on accepted human-face crops. A false or missing face must not select the general branch's model.
3. Keep whole-image and per-face scores separate. Heuristics, OCR/scene observations, filename clues and editable metadata never vote as extra classifier probabilities.
4. Implement a new versioned policy (proposed image-general-v4). Do not repurpose image-vit-v3 or overwrite its existing release artifacts. Bind validation to the selected general model, optional specialist, processor, detector and execution backend identities.
5. Freeze the aggregation rules before final testing. A low face score cannot cancel strong whole-image evidence. Conflicting decisive whole-image and face evidence requires review unless the specific combination has an independently validated rule. No majority voting among correlated heuristics and no arbitrary weighted average.
6. Distinguish prediction unavailable from scope unsupported and decision inconclusive. If no qualified general model exists yet, report that limitation and retain review/unsupported outcomes rather than invent a general-image verdict.

Gate: a non-face scene is never assigned a face-derived whole-image score. Provider failure, no face and conflicting branches each take the documented route. The hovercar's expected AI alert is a measured model outcome, not a hardcoded requirement based on filename, appearance or a one-image threshold adjustment.

## Phase 5 — Metadata and decision semantics

1. Preserve clue source, generator string and authentication status. Distinguish filename text, editable metadata/binary strings, and independently verified signed provenance. Do not claim C2PA validation without actual signature/trust verification.
2. Display the supplied image's clue as 'AI-generator metadata clue: Chatgpt — unverified'. This is separate from the model verdict. Removing/adding that string must not directly flip model scores.
3. Use explicit semantic states: likely AI-generated (validated model boundary), low detected AI signal (not verified real), review required (ambiguous/unvalidated/conflicting), unsupported (scope), and unavailable (execution).
4. Expose machine-readable per-branch status/scope/model/backend, score availability, policy validation, provenance clues, accepted face boxes and missing checks. Reuse current fields where possible; introduce backward-compatible optional additions. Missing score remains unavailable even if legacy transport requires a numeric placeholder.

Gate: metadata spoofing/removal tests, error-state tests and cross-view status consistency. A key or a weight file alone never sets decision_policy_validated=true.

## Phase 6 — Accurate original UI and PDF reports

Primary files: frontend/src/services/verdict.ts, views/ReportView.tsx, services/pdfExporter.ts and existing scan/history presentation.

1. Keep the original visual design. Show actual general/face scope and execution mode, distinguish uncalibrated model signal from correctness confidence and surface missing checks.
2. Fix restored history/report numeric cutoffs so backend review/unsupported/unavailable states cannot become 'safe' or 'higher-risk' solely from a placeholder or index. Apply the same semantic adapter to summary, history, narration and PDF.
3. Replace success-like missing-text fallbacks with status-specific wording: skipped means not run; failed means failed; absent evidence means not supplied.
4. Replace the fabricated UUID Hash with the backend input_sha256. If absent, print unavailable. Remove certification/verified-chain-of-custody claims unsupported by evidence.
5. Export the actual scope, branch statuses, generator clue/authentication status, active model/backend identity and policy validation state. Historical scans are not relabelled as if rerun; offer a fresh scan through the existing workflow.

Gate: JSON, screen and PDF agree on one shared result. Render and inspect long/multipage exports. No 'all clear' for skipped checks, fabricated hashes or confidence percentages without calibration. Original UI layout remains intact.

## Phase 7 — Independent validation and release

1. Build independently labelled validation and final-test manifests spanning modern generated scenes/objects/portraits and genuine camera images, plus CGI, illustrations, screenshots, recompression and messaging-app-like resizing. Decide whether non-AI CGI/art is outside the selected binary task rather than falsely assigning it a camera/AI label.
2. Group source derivatives, known subjects and generators appropriately; audit exact/near duplicates and known upstream overlap. Document unknown pretrained-data membership. Keep operating-point selection separate from final testing.
3. Select thresholds on validation data, then freeze model/processor/localizer/backend/policy identities and test once. Reuse existing audit/benchmark/promotion structure while extending it for the new model/task; the current ViT-only promotion code is not automatically compatible.
4. Measure real-photo false positives, generated-image misses, abstention/scoring/accepted coverage, localization recall, critical slices, grouped intervals and p50/p95 latency. Set error budgets before final testing. Retain the existing strict gates for the old face policy; do not transplant its sample-size assumptions unexamined to a new task.
5. Activate a released policy only after its measured gates pass. Preserve the prior configuration/model/policy for rollback. If data or quality gates are unmet, ship the software plumbing with the candidate disabled and report review-required honestly; document the remaining blocker.

Gate: repeatable independent evaluation and controlled end-to-end testing of API, stored report, history and export. Monitor runtime/provider errors and labelled performance separately. No guaranteed verdict on every generated image.

## Required regression matrix

| Case | Required behaviour |
| --- | --- |
| Supplied hovercar | Reject bogus building face; retain unverified Chatgpt clue; use general branch only when qualified |
| Same image with clue removed | Model score route unaffected by metadata removal; missing clue does not prove real |
| Genuine photo with forged Chatgpt string | Show unverified clue without forced AI classification |
| Clear real/generated portraits | Accepted face boxes; separate branch scores; no authenticity guarantees |
| Multiple/profile/occluded faces | Track accepted/rejected regions and incomplete coverage |
| Buildings/windows/vehicles | No face-specialist score for rejected proposals |
| No general model / wrong task | Unsupported or unavailable, not successful 0/50 score |
| 401/402/403/429/timeout/5xx | Distinct, bounded failure handling and explicit fallback mode |
| Wrong labels/partial distribution | Reject malformed prediction |
| Unvalidated policy/backend changed | No definitive released-decision claim |
| Skipped advisory analysis | Report 'not run', never 'no anomalies' |
| PDF digest absent | Show unavailable, never synthesize a SHA256 |

## Execution order and stop conditions

Baseline → backend contracts → face localization → general-model benchmark/routing → decision/metadata fields → original UI/export repairs → independent promotion and rollout. After each phase run the affected tests and verify that normal website scans and untouched modules still function. Use mock provider responses for most tests; distinguish those from approved live-provider checks and measured detection accuracy.

No UI redesign, new CNN training, automatic paid endpoint deployment, secret rotation, external upload of private fixtures, unconditional fallback or threshold reduction to satisfy one image is part of this plan.

## Primary references

- https://huggingface.co/dima806/deepfake_vs_real_image_detection — model identity, older-data/concept-drift limitation and linked face training notebook.
- https://huggingface.co/docs/inference-providers/tasks/image-classification — task API, inference permission, response and parameters.
