# Image detection: current audit and implementation plan

Date: 20 October 2026. Scope: the existing `dima806/deepfake_vs_real_image_detection` ViT, its image pipeline, decision policy, evaluation, training handoff and reporting. This is a plan; no product code is changed by this audit.

## Decision

Improve and evaluate the existing ViT pipeline first. Do not make a newly trained CNN a prerequisite for using that ViT. Keep the EfficientNet work as an optional experiment until independent evaluation justifies deployment. Do not lower thresholds to make the supplied portrait pass.

The earlier software repair reduced misleading authenticity claims, but introduced a CNN-first policy that does not match the clarified model choice. It remains useful for input security and honest reporting; its model requirement needs a deliberate revision.

## Evidence and limits

Inspected the current orchestrator, local/hosted inference, artifact loader, face localization, dataset preparation, policy evaluator, metrics and regression tests. Revisited the upstream model card. Reviewed the previously recorded authenticated portrait response at `runtime_state/image-release-v2/authenticated-api.json`; that response is historical evidence, not a newly repeated inference run.

The model is a fine-tuned ViT, not this project's independently trained EfficientNet. Its author warns about concept drift and recommends newer labeled training data: https://huggingface.co/dima806/deepfake_vs_real_image_detection . The warning supports a general limitation; it does not establish the exact cause of this portrait's scores. Upstream benchmark accuracy cannot be transferred to TrustNet uploads.

The recorded portrait has full-frame fake score 0.09/100 and face score 91.35/100. This proves view sensitivity for this example. It does not prove cropping fixes detection generally. Eye reflections, changed clothes and changed backgrounds are not sufficient standalone classification rules.

## Current findings

| ID | Priority | Finding and evidence | Required outcome |
|---|---|---|---|
| A01 | P1 | `inference/efficientnet_detector.py:71,171,192`: readiness and complete verdicts require a trained CNN; absent weights force partial/uncertain even when the requested ViT works. This is a product-policy mismatch, not a broken ViT download. | Explicit ViT policy with its own readiness and scope. Optional CNN absence cannot count as a required failure. |
| A02 | P1 | `evaluation/run.py:16`: evaluation refuses to run without that CNN; it cannot measure the actual ViT-only baseline. | Independent classifier and serving-policy evaluation modes, with consistent manifests and per-view records. |
| A03 | P1 | `huggingface_client.py:55` skips the face specialist for non-human inputs, but `efficientnet_detector.py:149` calls local inference anyway. A skipped scope decision becomes unrestricted full-frame classification. | One scope router shared by every backend; unsupported inputs remain unsupported, and missing faces remain unassessed rather than proven absent. |
| A04 | P1 | `local_vit_detector.py:120,131` takes the maximum across frame and up to four faces; the orchestrator uses fixed 25/70 disagreement and 40/62 decision thresholds. No local validation establishes those operating points. | Retain separate scores; compare aggregation policies on validation data and lock thresholds before final testing. |
| A05 | P2 | `face_analyzer.py:72,121`: eye-pair filtering rejects proposals without two detected eyes; tilt search runs only if no faces were found. Profiles, glasses, occlusion and mixed tilted/frontal groups can be missed. Runtime availability does not measure recall. | Annotated localization evaluation and quality/coverage reporting; replace the localizer only if measured results justify it. |
| A06 | P1 | `training/prepare_kaggle.py:47,56`: unusable face detections are excluded, and policy test data includes only retained images. The benchmark therefore hides localization failures and selection bias. | Keep an all-input serving holdout, with excluded cases and denominators reported. Separate classifier crops from end-to-end policy tests. |
| A07 | P1 | Current real-data evaluation has no modern-generator holdout, verified subject grouping or measured robustness. The prepared older GAN-face dataset cannot establish those properties. | Source-aware, duplicate-aware splits and independent recent-generator testing. Describe unknown provenance explicitly. |
| A08 | P2 | ViT results expose model revision, but root metadata declares the CNN's preprocessing string (`efficientnet_detector.py:242`). Actual ViT preprocessing comes from `AutoImageProcessor`; hosted frame and local faces can also use different revisions. | Per-view model, backend, processor/config hash, crop policy and transform identity. Do not imply preprocessing equivalence. |
| A09 | P2 | `huggingface_client.py:72` declares JPEG while the orchestrator supplies canonical PNG bytes. Hosted inference is optional and disabled by default, but this path is inconsistent. | Local execution by default; correctly typed payloads and explicit backend/revision records if hosted support remains. |
| A10 | P2 | All required texture/compression proxies currently gate completeness although they do not determine the classifier score. Their failure can force abstention for an unrelated classifier. | Define mandatory decode/model/scope checks separately from advisory diagnostics. Keep advisory failures visible. |
| A11 | P2 | `evaluation/run.py:39` hardcodes a 0.62 classification threshold; evaluation lacks per-generator metrics, uncertainty intervals, paired transform analysis, calibration and detailed failure reasons. | Versioned evaluation with failure/abstention denominators and configurable, frozen policy thresholds. |
| A12 | P2 | Existing Kaggle notebook trains EfficientNet, not the clarified ViT. Local ViT docstring still describes removed anomaly-weight fusion and earlier cloud behavior. | Correct documentation and a separate ViT fine-tuning notebook only after baseline/data gates. Preserve the optional CNN artifact for comparison. |

Paths in this table are relative to `models/image_deepfake/`. P1 means it blocks a defensible detection release; it does not imply an Internet-facing security incident. A01–A06 and A08–A12 follow directly from source inspection. A07 and the author's drift warning identify unmeasured risks; their impact requires data.

## Phased implementation

### Phase 0 — Freeze the baseline and acceptance contract

Tasks:
- Save current revision, dependency versions, model commit, processor configuration/hash, hardware, policy version and sanitized environment switches. Do not package credentials or user images.
- Define the first supported scope as human-face AI screening. Separate fully synthetic images, face edits/swaps and general images in the test labels and UI scope.
- Preserve the portrait as a private regression example with consent-controlled storage. Record full frame and face outputs without assigning a desired test score.
- Capture the current v2 baseline and add a ViT-direct baseline. Preserve input hash, boxes, view scores, failures and latency.

Deliverables: baseline manifest, scope specification and acceptance checklist. Exit: one input can be traced from upload bytes to model views, response, history and PDF; unsupported and failed cases are explicit.

### Phase 1 — Establish one ViT inference contract

Files: `inference/local_vit_detector.py`, `huggingface_client.py`, `efficientnet_detector.py`, service readiness and configuration.

Tasks:
- Introduce an explicit versioned policy selection, initially keeping v2 as a rollback path. New ViT policy requires its pinned model, processor and required runtime, not EfficientNet weights.
- Centralize scope routing before local or hosted execution. Preserve an unknown/unsupported state; a scene heuristic must not certify that a missed face is absent.
- Use shared EXIF/RGB decoding, record processor resize/crop/normalization independently from CNN transforms, and keep consistent provenance per view.
- Keep frame scores diagnostic until their role is validated. Return face scores and quality independently; never claim whole-image authenticity from one face.
- Separate liveness, model readiness, inference failure, unsupported input, incomplete coverage and ordinary model uncertainty. Keep absent diagnostic scores null.
- Keep hosted calls off by default. If enabled, correct media type and preserve backend/revision differences; do not silently mix them.

Verification: local-only startup, missing/corrupt model, malformed labels, processor mismatch, decode failures, no face, profile/occlusion, more than four faces, hosted failure and concurrent requests. Test that optional CNN absence does not block the ViT policy, and scope skips cannot fall through to local inference.

Exit: authenticated API and browser show the same selected policy and model state; no silent model/scope substitution. This phase improves correctness, not measured accuracy.

### Phase 2 — Build the evaluation dataset and runner

Files: `evaluation/run.py`, manifest schema, dataset preparation, new evaluation tests and documentation.

Tasks:
- Add modes for direct ViT, each view strategy and full serving policy. ViT baseline execution must not instantiate or require CNN weights.
- Extend manifests with sample/source/generator identifiers, task label, label evidence, original/derived linkage, known subject group and split. Keep unknown identifiers unknown.
- Separate training, model-selection validation, calibration and final test. Group source originals and all resized/compressed derivatives together. Remove exact duplicates and investigate near duplicates across splits.
- Add recent generated portraits and genuine camera portraits, plus difficult real photos, screenshots, retouching, low light, profiles, groups and non-face negative controls. Use verified labels and licenses. Do not classify uncertain Internet images as ground truth.
- Reserve an unseen generator/source holdout. If upstream ViT training membership is unknown, disclose possible pretraining overlap; use newly created independent examples for a stronger external test.
- Retain all localization failures in the end-to-end holdout. Report selection/exclusion counts per class and source.
- Save per-view probabilities/logits where available, boxes, quality, statuses, reasons and timings. Evaluate JPEG quality 95/75/50, resizing and screenshot-like transforms as separately named derived tests. They do not reproduce every WhatsApp transformation.

Metrics: ROC-AUC, PR-AUC, confusion matrix, false-positive and false-negative rates, fake recall at fixed real-photo false-positive rates, accepted coverage/error, abstention, unsupported/failure rate and p50/p95 latency. Report denominators and group-bootstrap confidence intervals; correlated crops/derivatives are not independent samples.

Exit: deterministic reports for the same checkpoint/policy/manifest; failures and abstentions cannot disappear from denominators. A 200-image sample is a smoke evaluation, not a release benchmark. Approximately 1,000 independent real examples is an initial minimum for investigating a 1% false-positive target; report the interval and expand data as needed.

### Phase 3 — Select localization, crops and decision policy

Dependencies: Phases 1–2. No training required yet.

Tasks:
- Annotate face boxes and measure recall/precision by face size, pose, occlusion and group count. Compare the current cascades with one locally deployable detector if the baseline fails. Record model license and pinned weights before adoption.
- Compare tight crops, a small predefined padding grid and the original frame. All candidates use identical model weights and paired validation examples; final test remains untouched.
- Compare face-only decisions, current maximum aggregation and a conservative region policy. Maximum aggregation can increase false positives as face count grows, so report group-size slices.
- Select low/high decision boundaries on validation data under a declared false-positive budget. Start with a proposed 1% real-photo false-positive target; it is a release criterion to validate, not a current claim. Report recall and coverage at that point.
- Keep disagreement and quality reasons explicit. A low frame score must not automatically cancel strong face evidence unless validation supports that rule. Do not use hand/eye/background heuristics as voting rules.
- Calibrate only if sufficient separate data exists; fit temperature scaling on calibration data and report held-out reliability, Brier score and calibration error. Otherwise continue displaying uncalibrated scores.

Exit: frozen detector/crop/aggregation/threshold policy plus validation report. Select based on operating-point performance and coverage, not the supplied portrait alone. If reliable thresholds cannot be established, retain review-required outputs and document the unmet criterion.

### Phase 4 — Fine-tune the existing ViT only if needed

Dependencies: baseline demonstrates a material gap; licensed recent training data and independent holdouts are ready.

Tasks:
- Prepare a separate Kaggle GPU notebook for the pinned ViT and its processor. Do not relabel the existing EfficientNet notebook as ViT training.
- Compare frozen pretrained ViT, head-only tuning and controlled unfreezing with a small predefined search. Record seeds, augmentations, learning rates, checkpoints and early stopping on validation only.
- Include genuine compressed/retouched photos and recent synthetic portraits; monitor false positives and historical-generator forgetting. Keep all derivatives/groups within their original split.
- Extend the artifact contract for ViT architecture, class mapping, processor/crop version, source revision, weight/config hashes, dataset provenance and evaluation/policy identity. The existing loader only accepts EfficientNet.
- Run the exact serving policy on the untouched test set. Compare against the frozen baseline with paired uncertainty estimates. Keep EfficientNet as an optional comparator if compute permits; do not add an ensemble without demonstrated benefit.

Exit: candidate improves the agreed recall/false-positive/coverage tradeoff on independent data without material regressions in critical slices. Otherwise retain the baseline and record the failed experiment. Training completion alone is not a promotion gate.

### Phase 5 — Product integration and release verification

Files: image service, gateway, scan management, trust fusion, `imageAssessment.ts`, `verdict.ts`, `ReportView.tsx`, `pdfExporter.ts` and setup checks.

Tasks:
- Show supported scope, assessed regions, active model/policy, coverage and score definition. Distinguish likely synthetic signal, low detected signal, review required, unsupported and failed states.
- Keep score separate from confidence and reliability. Explain whether a number refers to a face or the frame. A whole-image trust score must not imply camera provenance.
- Version historical results; preserve old policy identity and rescan guidance. Confirm status and reasons survive API, database/history, trust fusion and PDF serialization.
- Keep existing upload/security limits and authentication. Verify service-port behavior and project startup after policy/config changes.

Exit: affected regression suite, frontend build/lint, real authenticated upload and browser/PDF checks pass for real/AI, disagreement, no-face, degraded input and missing-model cases. Review desktop/mobile states. Test inference on the target CPU environment as well as the Kaggle GPU training environment.

### Phase 6 — Controlled promotion and monitoring

Tasks:
- Package an immutable versioned model, processor and policy together. Validate hashes before activation; retain the prior version and a one-step configuration rollback.
- Run candidates in shadow comparison on approved test inputs before switching the default. Store minimal operational metadata; do not introduce retention of private images without an explicit product decision.
- Monitor failure/unsupported/abstention rates, latency and score drift by version. Drift is a signal to investigate, not proof of changed accuracy. Accuracy monitoring requires newly verified labels.

Exit: documented promotion decision, rollback exercise and evaluation report tied to the deployed hashes. If scientific/data gates remain unmet, release only as explicitly limited screening with abstention; do not advertise detection accuracy.

## Order and stop conditions

Implement Phases 0–2 first, then choose crops and thresholds in Phase 3. Training is conditional in Phase 4. Complete product and release checks in Phases 5–6. Independent data collection may proceed alongside software work. GPU training is the previously selected execution environment, not authorization to upload private portraits.

Do not spend time on an additional CNN, visual heatmaps, a new dashboard or more heuristic engines before the ViT baseline is measurable. Stop architecture expansion when the existing ViT meets the declared operating point. If it fails, the measured failure slices determine the next data/model experiment.

## Acceptance checklist

- ViT-only policy works without a separate CNN artifact and has truthful readiness.
- No out-of-scope fallback, invented confidence or absent-score substitution.
- Localization failures remain in end-to-end evaluation.
- Validation selects the policy; independent test data evaluates it once.
- Metrics include false positives, false negatives, coverage, failures and uncertainty by source/generator.
- Browser, history and PDF preserve region-level evidence and policy identity.
- Modern-generator accuracy remains unclaimed until independently measured.

## Current verification

Fresh focused contract tests: **29 passed in 32.51 seconds**, covering screening v2, frame/face view policy and evaluation leakage checks. These include mocked model outputs and establish contract behavior only. The previous 152-test run is historical software evidence only; neither run establishes real-world detection accuracy. No model training, threshold changes or production code edits were performed for this plan.
