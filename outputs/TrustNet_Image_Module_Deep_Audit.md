# TrustNet AI: deep audit of the image module

Audit date: 20 October 2026 (Asia/Kolkata).

## Conclusion

The current image module is a heuristic screening system supported by an externally pretrained face ViT. It is not serving the project's trained binary EfficientNet checkpoint. The recent face-crop repair exposes the supplied portrait's conflicting model evidence, but does not resolve the module's wider correctness, training, security, and reporting defects.

This audit identifies 16 actionable findings: four P1 and twelve P2. Priorities reflect consequences and the currently inspected development deployment, not proof of public Internet exposure. No implementation fixes were made during this audit. Existing user changes were preserved; only audit scripts, generated benign fixtures, and this report were added.

## Scope and evidence

Inspected training, dataset loading, evaluation metrics, configuration, preprocessing, the EfficientNet orchestrator, local and hosted classifiers, all forensic analyzer families, Grad-CAM, image-service REST and Kafka integration, the scan-management image entry point, gateway detection proxy, trust fusion, setup verification, and image UI/PDF reporting.

Fresh complete image test run, including training and evaluation unit tests: **96 passed, one warning, 57.18 seconds**. These are software regression tests, not a representative detection-accuracy evaluation. Frontend image-display contract and OpenCV face/eye resource checks also passed. The probes below demonstrate behavior not protected by those green tests.

Reproduction scripts and machine-readable results:

- `runtime_state/image-module-audit/probe.py` and `probes.json`
- `runtime_state/image-module-audit/boundary_probe.py` and `boundary-probes.json`

The probes use generated harmless fixtures, mocked classifier votes, and simulated component failures. No user image was uploaded to an external inference provider during this audit. The resource probe validated a large compressed image without running expensive forensic allocations.

## Findings

### F01 — P1: The trained CNN is disconnected from serving

**Source:** `models/image_deepfake/inference/efficientnet_detector.py:58`, `:313`, `:729`; `models/image_deepfake/training/train.py:23`, `:166`.

Training builds a two-class EfficientNet head and saves `best_model.pt`. Serving instead constructs ImageNet EfficientNet-B0, never calls `load_state_dict`, and extracts feature variance. That variance is included in evidence but is not an input to the fused anomaly-weight list. Its ImageNet Grad-CAM does not attribute the ViT or final risk score. A training success on Kaggle would not by itself change predictions in this implementation.

**Impact:** The product's CNN model identity and actual deepfake classifier differ. Restoring a deleted checkpoint alone is insufficient unless serving is wired to its architecture and preprocessing.

**Required repair:** Introduce an explicit model-artifact loader with a strict two-class architecture, label mapping, checkpoint hash, training/preprocessing metadata, readiness validation, and failure behavior. Do not silently substitute ImageNet classification when trained deepfake weights are missing.

### F02 — P1: Failed forensic analyzers become reassuring votes and successful coverage

**Source:** `models/image_deepfake/inference/efficientnet_detector.py:272`, `:328`, `:883`, `:901`, `:907`, `:960`; analyzer exception returns in frequency, Gabor, ELA, pixel, and noise modules.

Several exception paths return low numeric anomaly scores. Fusion includes those scores without checking analyzer status. Pixel and noise failures lack an explicit failure status; telemetry hardcodes APPLIED for pixel, ELA, and noise. Completeness checks consider localization and learned views, but not these failed forensic checks.

**Reproduced:** Five analyzers forced through their actual invalid-input exception returns, while processing a valid generated fixture with a mocked low-risk classifier vote: risk **6.41**, status **SUCCESS**, verdict **AUTHENTIC**, coverage **true**, agreement **0.98**. ELA itself reported FAILED; FFT/Gabor reported FALLBACK.

**Required repair:** Use a consistent analyzer result schema. Exclude failed/unavailable results from fusion and agreement, propagate truthful statuses, and define mandatory versus optional checks. Incomplete required checks must prevent an authenticity-style verdict. Test failure combinations at the orchestrator boundary.

### F03 — P1: Unauthenticated storage-key inference escapes the storage root

**Source:** `services/image_deepfake/app/worker.py:43`, `:51`; `services/image_deepfake/app/router.py:74`; `gateway/app/routers/detect_routes.py`.

The worker accepts any existing absolute file path before performing its storage-root check. The subsequent `startswith` check is a string-prefix test, not a canonical filesystem containment check, and does not establish symlink/junction containment. The direct detection routes have no authentication dependency; the gateway detection proxy also forwards without its authentication dependency.

**Reproduced:** A generated PNG outside the configured storage directory was accepted by `/detect/key` with **HTTP 200**, no Authorization header, and inference invoked. The worker separately returned the bytes of a harmless generated `.bin` fixture outside storage.

**Impact:** Callers who can reach this route can request processing of local files beyond the intended storage root. Derived metadata may be exposed, and oversized files can be read into memory. This audit does not claim unrestricted raw-file exfiltration or Internet exposure.

**Required repair:** Remove the absolute-path exception, resolve canonical paths and verify containment, enforce ownership and authorization, restrict internal worker access, and apply shared media validation to file, storage-key, and event paths.

### F04 — P1: The shipped training entry point cannot complete its documented workflow

**Source:** `models/image_deepfake/configs/baseline_config.yaml:10`; `models/image_deepfake/training/train.py:143`, `:161`.

The baseline config defines `dataset.batch_size`; the trainer reads `training.batch_size`. The config also lacks the real-data manifests required by the trainer. Several advertised settings are not consumed: scheduler, early stopping, mixed precision, label smoothing, configurable model/dropout, workers, and face-crop margin.

**Reproduced:** Running `run_training` with the shipped config and explicit dry-run mode raises **KeyError: 'batch_size'** before training. A single-class validation set produces AUC=None; a controlled runner probe then raises **TypeError: unsupported format string passed to NoneType.__format__** at the metrics-print statement.

**Required repair:** Validate a single explicit config schema before creating outputs; require class coverage where AUC is mandatory; format unavailable metrics safely; implement advertised settings or remove them. Add a CLI-level training smoke test, rather than only testing individual training functions.

### F05 — P2: A file-security finding changes the AI-authorship verdict

**Source:** `models/image_deepfake/inference/efficientnet_detector.py:527`; `models/image_deepfake/forensics/steganography_analyzer.py:50`.

Any detected appended payload forces an AI/manipulation screening floor of 85/100. Payload presence can be relevant to file safety, but does not demonstrate AI generation or pixel manipulation.

**Reproduced:** The same synthetic audit fixture and mocked low-risk model vote moved from 6.41/AUTHENTIC to **85/LIKELY_AI_MANIPULATED** after appending a harmless test trailer beginning with ZIP magic. The explanation reported a covert payload, not visual generation evidence. No actual ZIP archive or malicious executable was used.

**Required repair:** Report file-security risk separately from image authorship/manipulation. Preserve the payload warning without treating it as learned AI evidence or cryptographic provenance.

### F06 — P2: Malformed classifier output is accepted as successful inference

**Source:** `models/image_deepfake/inference/local_vit_detector.py:148`; equivalent hosted parsing in `huggingface_client.py:96`.

The parser defaults both class scores to 0.5 and matches broad substrings, including `AI`, instead of validating the configured model's exact labels and complete probability output. It does not require both expected classes or verify probability normalization. The newer multi-view numeric validator does not repair the underlying single-view parser.

**Reproduced:** An empty result and an UNKNOWN label both return applied=True, score=50, label=fake. A custom label PAINTING with score .99 is interpreted as fake=99 because it contains `AI`.

**Required repair:** Pin an explicit model contract and exact class mapping, request the full expected label distribution, reject missing/unknown/non-finite/out-of-range outputs, and mark inference unavailable instead of manufacturing neutral votes.

### F07 — P2: Image orientation and canonical decoding are inconsistent with display

**Source:** `models/image_deepfake/preprocessing/transforms.py:25`; separate Pillow decoding in classifier and forensic modules.

Image bytes are converted directly to RGB without applying EXIF orientation. Browser display can honor that orientation while classifiers, face boxes, and optics calculations use the stored pixel orientation. Each analyzer decodes separately, without a shared canonical image contract. Animated or multi-page formats also lack an explicit frame-selection policy.

**Reproduced:** JPEGs with identical pixels and different orientation metadata produce identical inference tensors, while display-correct orientation changes the test image from 80×40 to 40×80.

**Required repair:** Validate/decode once, apply a documented orientation and color/frame policy, and consistently map all coordinates to that representation. Retain original bytes separately for metadata and trailer checks.

### F08 — P2: Encoded byte limits do not bound decoded memory or inference work

**Source:** `services/image_deepfake/app/router.py:31`; `preprocessing/validator.py`; `efficientnet_detector.py:189`; storage-key reads in `worker.py:45`.

Uploads are fully read before their byte-size check. There is no application-level decoded-pixel budget applied consistently across entry points. Multiple analyzers independently decode full-resolution images and allocate float arrays in a seven-thread pool per scan. Storage-key/event paths bypass the upload checks. Pillow's own extreme-image protection is not an application memory budget.

**Reproduced:** A **5000×5000** JPEG of **392,502 bytes** passes the validator. The audit deliberately did not run its full parallel forensic workload.

**Required repair:** Bound upload reads, file reads, dimensions, pixels, animation frames, concurrent jobs, and expensive analyzer resolution. Keep full-resolution analysis only where justified by an explicit budget. Add bounded resource tests rather than stress-testing the user's machine.

### F09 — P2: PDF chain-of-custody and certification claims are fabricated

**Source:** `frontend/src/services/pdfExporter.ts:355`, `:360`, `:361`.

The PDF labels `sha256:${scan.id}-${Date.now().toString(16)}` as a UUID hash under “CHAIN OF CUSTODY & VERIFICATION DIGEST.” This is a scan identifier plus timestamp, not a SHA-256 of the original bytes or report. “Certified by” is also printed without a verification mechanism.

**Impact:** Exporting the same scan changes the supposed digest. Readers may infer integrity or certification guarantees that the implementation does not provide.

**Required repair:** Remove unsupported certification language. If integrity is required, compute and persist the actual original-content hash with algorithm, timestamp, model identity, and a clearly defined verification procedure. Do not present a display identifier as cryptographic evidence.

### F10 — P2: PDF export hides failed and unavailable analyzer states

**Source:** `frontend/src/services/pdfExporter.ts:221`.

The PDF prints APPLIED only for APPLIED; every other status becomes SKIPPED. FAILED, FALLBACK, and UNAVAILABLE lose their meaning. This compounds F02 and can make a failed check look intentionally omitted.

**Required repair:** Preserve the exact supported status and failure reason across API, UI, PDF, and stored records. Add report assertions for all failure states, not only disagreement scores.

### F11 — P2: Forensic labels and physical conclusions exceed the measurements

**Source:** `forensics/noise_analyzer.py:19`; `pixel_morphing_analyzer.py:37`; `physics_eye_reflection_analyzer.py:113`, `:130`, `:150`; `geometry_physics_analyzer.py`; telemetry names in `efficientnet_detector.py:905`.

The “PRNU” analyzer measures a single image's grayscale blur residual, without a reference sensor fingerprint. The CFA proxy measures green-channel parity differences rather than verifying a camera demosaicing history. “Face X-Ray” is a boundary-gradient heuristic, not a trained Face X-Ray model. Geometry is based on ORB keypoint balance and bottom-edge density, not reconstructed 3D support physics.

The eye module thresholds an entire Haar eye box at brightness 200, selects its largest bright contour, and compares vectors measured from box centers. It does not segment iris/pupil/cornea or distinguish sclera, skin, glasses, and multiple lights. Its APPLIED finding can nevertheless assert a severe physical lighting violation and feed strong-domain corroboration.

**Required repair:** Name these as measured proxies, avoid physical verification claims, record localization/quality failures, and validate each signal against independently labeled controls before granting it strong decision authority. Missing or asymmetric catchlights alone must not determine AI authorship.

### F12 — P2: Model readiness and recovery are not tied to service health

**Source:** `inference/local_vit_detector.py:40`, `:50`, `:54`, `:57`; `services/image_deepfake/app/main.py:77`; `inference/huggingface_client.py:45`.

The ViT loads lazily, is forced to CPU, and has no pinned model revision. A first load failure sets `_load_error`, preventing retry for the process lifetime. `is_configured()` still returns True, and `/health` returns ok without verifying classifier availability or localization resources. Concurrent cold requests can race the unguarded initializer. The same mutable Grad-CAM object also stores activations/gradients across threaded requests without isolation.

The optional token check uses `future.result(timeout=2)` inside a ThreadPoolExecutor context. Context exit still waits for the worker, so that is not a reliable two-second startup deadline. These lifecycle/concurrency risks are source findings; no production concurrency load test was performed.

**Required repair:** Separate liveness/readiness, verify artifacts before accepting inference, serialize initialization, implement bounded recoverable loading, pin model identity, isolate explanation state, and measure device/latency behavior. Use actual network deadlines instead of waiting on an unbounded executor task.

### F13 — P2: Face-crop coverage can be overstated after missed detection

**Source:** `forensics/face_analyzer.py:84`, `:89`, `:130`; `forensics/scene_analyzer.py:81`, `:97`; `inference/efficientnet_detector.py:272`.

The repaired detector requires a plausible eye pair, which rejects background proposals but also misses profiles, occlusions, closed eyes, and some small or tilted faces. Rotation sweeps run only when no face was accepted, so a frontal face can suppress a search for a second tilted face. The four-face classifier bound is explicit and good, but cannot account for faces never detected.

A missed face only causes incomplete portrait coverage when the separate color/texture scene heuristic labels the image a portrait. That scene heuristic uses skin-color thresholds and fixed confidence constants. If it labels a real portrait as another scene, full-frame-only analysis can still claim complete coverage. Both classifier constructors discard `general_model_name`, so there is no implemented general-image model despite dual-model comments.

**Required repair:** Define coverage as coverage of detected regions, not all people. Evaluate localization recall across varied people, lighting, poses, and occlusion; use a supported general-image detector for whole-scene authorship. Ensure abstention policy does not depend solely on a skin-color scene heuristic.

### F14 — P2: The application's actual image route loses status and source persistence

**Source:** `services/scan_management/app/routers/scan_router.py:124`, `:169`, `:182`; `frontend/src/services/api/scan.api.ts:18`, `:34`.

The UI uses `/scans/analyze`, which instantiates the detector inside scan management instead of calling the dedicated image service. It accepts PARTIAL_SUCCESS but writes SUCCESS in the outer scan and database row. The nested result retains partial status, so the current report may still warn, while scan history and other consumers receive inconsistent status.

This route does not persist source bytes or a media storage key. The frontend supplies a temporary object URL for the current upload only. A fresh history load cannot reconstruct the image preview from this saved record. Separate entry points also duplicate model instances and validation policies.

**Required repair:** Propagate detector status consistently. Decide and document source-retention behavior; persist an authorized preview/reference if history inspection is supported, or explicitly show that the original is unavailable. Centralize the inference contract across direct and event paths.

### F15 — P2: Training outputs cannot establish reproducible model quality

**Source:** `training/train.py:123`, `:139`, `:146`, `:166`; `training/dataset.py`; `evaluation/metrics.py`.

The trainer checks identity strings across train/validation but has no integrated held-out test manifest, file-hash duplicate audit, generator-separated evaluation, seed control, or persisted run metadata. A state_dict alone lacks the dataset version, split evidence, label map, preprocessing, selected epoch, optimizer state, and evaluation report. Identity strings are caller supplied; the check does not establish that identities or source-image families were grouped correctly. Synthetic unit fixtures prove that training functions execute, not that a Kaggle model achieved useful accuracy.

**Required repair:** Preserve reproducible manifests, grouping/duplicate checks, seeds, configuration, metrics, model/hash metadata, and a held-out evaluation. Test the final served model and fused policy, not only a standalone CNN. A new real-data training run remains separate from this audit.

### F16 — P2: Score presentation and evidence do not explain the actual decision rule

**Source:** `inference/efficientnet_detector.py:402`, `:505`, `:527`, `:538`, `:550`, `:729`; `frontend/src/views/ReportView.tsx`.

The final index is altered by hand-written floors/caps, not just the displayed weighted engine estimate. Correlated image heuristics are grouped as independent corroborating domains without empirical independence evidence. The agreement statistic is `1 - std(scores)*0.45`, clamped to 0.60–0.98, so even disagreement produces an encouraging-looking percentage. Evidence `contribution` fields contain raw analyzer scores or feature variance, not measured contributions to final fused risk.

The visible spatial-saliency heatmap is a browser gradient visualization; browser ELA is recomputed after resizing to at most 640px, while server ELA uses another representation. They should not be mistaken for attribution of the classifier or fused decision. The prior fix correctly removed overall correctness confidence; it did not calibrate these remaining indicators.

**Required repair:** Record an auditable decision trace with applied rules and score changes, label raw measurements accurately, stop implying independence/calibration, and distinguish illustrative transforms from model attribution. Evaluate and calibrate the complete deployed policy on held-out data before reporting empirical confidence.

## Existing improvements that remain valid

- Automatic face crops now expose the supplied portrait's disagreement rather than relying only on whole-image inference.
- Invalid crop coordinates and non-finite crop scores are rejected; failed crops do not become zero-risk votes.
- Face inference is bounded to four regions and reports truncation as incomplete.
- Missing cascade resources are explicit, and setup checks the installed face/eye resources.
- Overall report confidence says “Not calibrated,” and model-view scores remain separate.
- Metadata strings and filenames are not treated as cryptographically verified generator provenance.
- Evaluation metrics validate binary inputs and preserve unavailable one-class metrics as None; F04 concerns the trainer consuming that correct None result unsafely.
- Kafka processing uses the shared reliable-consumer wrapper. This audit did not run a broker crash/recovery test or validate a deployed multi-service environment.

## Recommended repair order and acceptance gates

1. **Protect inference boundaries:** F02, F03, F08, and F10. Failure-injection cases must abstain or report incomplete checks; unauthorized/out-of-root keys must fail before reading; pixel and memory budgets must apply to every entry point.
2. **Restore the training-to-serving contract:** F01, F04, F06, F12, and F15. The documented CLI must complete a smoke run, save a verifiable artifact, and load that exact artifact in serving with identical labels and preprocessing. Missing weights must fail readiness.
3. **Separate evidence meanings:** F05, F07, F11, F13, and F16. File safety must not become an AI-authorship verdict, orientation must be consistent, weak localization must not claim full coverage, and heuristic transforms must not masquerade as physical verification or model attribution.
4. **Repair saved reports:** F09 and F14, plus status consistency from F10. Stored partial results must remain partial; hashes must be real or omitted; historical-image availability must be explicit.
5. **Measure real performance:** Only after these software gates pass, run an independently labeled real-camera and modern-generator evaluation, including resized/recompressed images, unseen generators, and hard real-photo controls. Measure false positives, false negatives, abstention rate, subgroup/pose coverage, calibration, latency, and resource usage.

Do not force the supplied portrait into a desired label or train on it and then count it as independent test evidence. Existing passing tests and the earlier four variants of one portrait do not establish population accuracy, production readiness, or recovery of the deleted Kaggle checkpoint.
