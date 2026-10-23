> Historical v2 policy reference. The current default is ViT-only v3; see [current operations](image-vit-v3.md). The CNN requirement below applies only when v2 is explicitly selected.

# Image screening v2

The image audit remediation replaces the previous heuristic fusion policy. The trained binary EfficientNet checkpoint is the primary classifier. A pinned face ViT provides secondary frame/face observations and a diagnostic fallback. Neither score is calibrated correctness confidence.

## Current operational state

No trained project checkpoint is installed. The local application can return **PARTIAL_SUCCESS / UNCERTAIN** screening results using cached ViT weights, but `/ready` returns 503 until a valid trained artifact is installed. `/health` is liveness only. The recent software tests do not establish detection accuracy.

The user selected Kaggle GPU training with `xhlulu/140k-real-and-fake-faces`, version 2. Its description identifies 70k real FFHQ/Flickr faces and 70k GAN-generated faces resized to 256px. It is a face/GAN benchmark, not evidence of general-image or modern diffusion-generator performance. Source: https://www.kaggle.com/datasets/xhlulu/140k-real-and-fake-faces . Upstream FFHQ metadata: https://github.com/NVlabs/ffhq-dataset . Kaggle lists the license as “Other (specified in description)”; retain upstream license and attribution information.

## Phase 1: Boundaries and failures

- Both direct image uploads and gateway detection routes require signed access tokens. Public storage-key inference is forbidden; trusted Kafka workers resolve relative keys inside their canonical storage root.
- Image body middleware bounds declared and streamed request bytes before multipart parsing or gateway buffering. Reads are bounded to the configured image byte limit plus one byte. Multipart transport has 64KiB overhead allowance.
- Default decoded budget: 4,000,000 pixels and 4096px maximum side. Animated/multi-page media are rejected. Pixel decoding is checked, not only file signatures.
- Canonical inference pixels use EXIF orientation and RGB conversion. Metadata, recompression-history and trailer inspection retain original bytes. ICC color-profile certification is not claimed.
- One scan per detector runs at a time; additional inference requests return a retryable busy error. At most two full-resolution heuristic jobs allocate concurrently.
- Failed checks have unavailable measurements, cannot vote as low risk, and make required coverage incomplete. Every exported analyzer retains its actual status.

## Phase 2: Training and deployment contract

Training requires train, validation and test manifests of `[path, label, source_group]`, with **0=real and 1=fake**. Paths are relative to each manifest. Both classes, disjoint source-group strings and unique content hashes are required. The checks do not prove biometric subject separation when the dataset has no subject identities.

The Kaggle adapter preserves publisher splits, removes byte/decoded-pixel duplicates, and prepares the same Haar/eye-pair face crops used by serving. Images without one usable localized face are excluded and counted. Source-image grouping is explicitly weaker than verified identity grouping; the notebook reports that limitation. The full original test-image paths are retained separately for serving-policy evaluation.

The trainer supports a validated configuration, seeded randomness, early stopping, validation checkpoint selection, held-out test metrics, optimizer state, run history, manifest hashes, class mapping and preprocessing/input policy metadata. Exact reproducibility across different hardware/library versions is not guaranteed. Smoke runs use generated fixtures and produce **non-deployable** artifacts.

A deployable bundle contains `best_model.pt`, `manifest.json`, `dataset_index.json`, and the training report. Loading checks hashes, architecture, binary labels, scope, preprocessing/input policy, disjoint source groups and both classes in all splits. Loading uses `weights_only=True` and strict state-dict matching. No ImageNet fallback is substituted for missing trained weights.

Use the generated notebook and source ZIP under `outputs/image-training/`; see [Kaggle instructions](image-training-kaggle.md). Training is not automatically started on this machine.

## Phase 3: Meaning of evidence

The primary CNN's fake score is the screening index. If that checkpoint is unavailable, a ViT score can be displayed only as a diagnostic fallback and the result remains incomplete/uncertain. Heuristic measurements, generated vision explanations, filename strings, editable metadata and hidden-payload indicators do not change AI authorship scores.

Strong low/high disagreement across model views forces abstention. Missing required checks also force abstention. The provisional low/high decision boundaries remain explicit in the versioned policy; no empirical confidence is fitted. A low score is labeled LOW MANIPULATION SIGNAL, never verified authenticity. The public decision trace records score source, missing checks, disagreement and verdict.

PRNU, CFA, eye-lighting, boundary and geometry claims are replaced in serving telemetry by the measurements actually implemented. Eye highlights and edge distribution are advisory proxies, not reconstructed physical proof. Face coverage means **detected regions only**; missed people cannot be counted. Crops are bounded to four faces. The general-image CNN scope is separate from face scope; no silently ignored general-model argument supplies a general detector.

The ViT revision is pinned to `29e4cf9efc543845610045f6ba7e88e5cf9d9301` for the default face model. Initialization is serialized and failed loads can retry after a cooldown. Cached weights are used by default; `IMAGE_ALLOW_MODEL_DOWNLOAD=true` permits an explicit initial Hub download. CUDA is selected when available. Hosted inference is disabled by default; deployment evaluation uses local inference only. Do not claim a pinned hosted-provider revision.

## Phase 4: Reports and history

The original-byte SHA-256 is computed at inference and persisted with the result. PDF exports show that digest when available, do not fabricate a timestamp hash, and make no certification or chain-of-custody claim. Correctness confidence is shown as Not calibrated. Raw heuristic observations are not described as additive risk contributions or independent agreement percentages.

The scan route, completion path and trust engine preserve image PARTIAL_SUCCESS and disagreement. The live UI includes CNN availability, crop scores, missing coverage and file-safety warnings. Illustrative resized ELA/pixel-gradient views are not classifier attribution.

Original uploads on the direct analysis route are **not retained**. The current upload has a temporary browser preview; after history reload, users must upload the original again for inspection. The report states this explicitly. Older image results are marked RESCAN REQUIRED rather than silently relabeled under v2.

## Phase 5: Real-data evaluation

The Kaggle notebook evaluates the selected CNN on the retained publisher test split, and separately evaluates a deterministic balanced sample of original test images through the actual serving policy. It reports abstention, failures, accepted decisions and score metrics. The evaluator rejects known training/validation content and source groups. It does not claim identity-disjoint or unseen-generator validation without corresponding metadata/data.

No Kaggle training has been executed by this implementation task. Do not report benchmark accuracy until the notebook output exists. Additional modern-generator data, hard real-photo controls, pose/occlusion coverage, near-duplicate review and calibration remain necessary before general deployment claims.

## Checks and operations

From the project root:

```powershell
.\.venv\Scripts\python.exe scripts/checks/verify-image-runtime.py
.\.venv\Scripts\python.exe scripts/checks/verify-image-model.py
.\.venv\Scripts\python.exe -m pytest models/image_deepfake/tests services/image_deepfake/tests -q
node scripts/checks/test-image-assessment.mjs
node scripts/checks/test-image-report.mjs
```

The trained-model check is expected to fail until the Kaggle artifact is installed. `setup.bat --verify` includes this check. Frontend build/lint run from `frontend/`. Windows API tests need socket access for asyncio. Restart image and scan services after changing model artifacts. A versioned install can use IMAGE_MODEL_DIR; preserve the prior directory and switch that setting back for rollback. Never overwrite a known-good artifact with a smoke run.
