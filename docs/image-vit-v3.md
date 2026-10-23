# Existing ViT implementation and operations

The default policy is `image-vit-v3`, using the existing pinned `dima806/deepfake_vs_real_image_detection` locally. It assesses detected human faces. A separate CNN is not required or loaded. The earlier `image-screening-v2` remains explicitly selectable for rollback/comparison with its own CNN requirement.

## What changes

- One local backend processes every assessed view. No assessable face means UNSUPPORTED / no score; no classifier fallback bypasses scope routing. Missed faces remain possible.
- Face scores are preserved separately. The maximum face score is an uncalibrated screening index. Full-frame results are diagnostic and do not vote or cancel face evidence. No person identity or camera provenance is inferred.
- Decode, localization and assessed face-model availability determine required coverage. Texture/compression/file observations are advisory; their failures are visible but do not turn the face model into an unavailable classifier.
- Model readiness and operating-point validation are separate. `/ready` can return 200 with pinned model/processor/localization loaded while `decision_policy_validated` remains false. Until a validated policy passes independent final-test gates and is configured, verdicts remain review-required. Removing the CNN prerequisite does not fabricate scientific validation.
- Scope, score availability, model revision, processor configuration/hash, crop policy and required/advisory failures persist through reports. A missing score is shown as unavailable, not a low-risk zero. Existing numeric transport fields retain a placeholder where the shared schema requires a number; `score_available=false` is authoritative.
- Authentication, upload budgets, EXIF handling, storage containment and bounded concurrency remain enforced. Original uploads are not retained by direct scanning.

## Runtime and baseline

From the repository root:

```powershell
$env:IMAGE_ASSESSMENT_POLICY = 'image-vit-v3'
$env:IMAGE_ALLOW_HOSTED_INFERENCE = 'false'
# Cached model weights are used by default. Allow an initial public model download only if needed:
$env:IMAGE_ALLOW_MODEL_DOWNLOAD = 'true'
.\.venv\Scripts\python.exe scripts/checks/verify-image-model.py
.\.venv\Scripts\python.exe scripts/checks/capture-image-baseline.py --output runtime_state/image-v3/baseline.json
```

Restart image and scan processes after configuration changes. The local CPU runtime remains supported; Kaggle GPU is used for the optional training run. Liveness does not establish model availability, and model availability does not establish accuracy. The model author's concept-drift warning remains relevant: https://huggingface.co/dima806/deepfake_vs_real_image_detection .

## Evaluation manifests

Use JSON lists with records such as:

```json
[
  {"path":"photos/example.jpg","label":0,"group":"source-001","split":"test","source":"camera-set","generator":"none","task":"portrait","pose":"frontal","quality":"original"}
]
```

Labels are 0=real and 1=fake. Relative paths resolve against the manifest directory. Keep all derivatives and known subjects inside one split. Optional `subject_id` records only verified dataset metadata; never guess it. Legacy `[path,label,group]` rows remain accepted, with unknown source/generator metadata. Label evidence, licensing and independent source/generator provenance require dataset review.

The dataset audit checks exact bytes, decoded pixels, source groups and known subjects across supplied splits. Matching dHash buckets are review candidates, not exhaustive near-duplicate detection. A clean hash audit does not prove unknown identities are separated.

```powershell
.\.venv\Scripts\python.exe -m models.image_deepfake.evaluation.data_audit --train data/train.json --validation data/validation.json --test data/test.json --output outputs/data-audit.json
.\.venv\Scripts\python.exe -m models.image_deepfake.evaluation.benchmark --manifest data/test.json --mode vit_direct --purpose test --output outputs/vit-direct.json
.\.venv\Scripts\python.exe -m models.image_deepfake.evaluation.benchmark --manifest data/test.json --mode vit_policy --purpose test --robustness --output outputs/vit-policy.json
```

`vit_direct` is a full-frame diagnostic baseline, not a scope claim. `vit_policy` exercises actual localization, face scores, coverage and abstention. Neither requires a CNN. Malformed/decode failures remain in end-to-end denominators. Reports include class metrics at a clearly labeled reference threshold, source/generator/task/pose/quality slices, grouped bootstrap intervals, unsupported/failure counts and p50/p95 latency. Reference-threshold accuracy is not deployed-decision accuracy. Transforms include JPEG 95/75/50, 256px resizing and a screenshot proxy; they do not reproduce every messaging app.

Source-group intervals assume groups represent independent sources. Unknown upstream ViT training membership remains a limitation. Use recently collected independent data to reduce that uncertainty. No recent labeled dataset is currently supplied, so no modern-generator accuracy or scientific promotion is claimed.

## Localization and crop comparison

Localization annotations must include `boxes` as `[x,y,width,height]` in the EXIF-oriented image and `coordinate_space: "exif_oriented_rgb"`. An explicit empty box list is a verified no-face annotation; a missing list is rejected.

```powershell
.\.venv\Scripts\python.exe -m models.image_deepfake.evaluation.localization --manifest data/face-boxes.json --output outputs/localization.json
.\.venv\Scripts\python.exe -m models.image_deepfake.evaluation.view_experiments --manifest data/validation.json --output outputs/crop-comparison.json
```

The localization report uses IoU 0.5 and reports recall/precision by pose/quality. Crop comparison records paired full-frame, face-max and face-mean scores with padding 0/10/20%. It does not change serving behavior. The deployed candidate contract currently supports only zero-padding face-max; adopting another strategy requires a new versioned contract and validation. Do not choose a detector or crop because one supplied portrait looks better.

## Policy selection and promotion

Keep validation and final-test evidence inside one new version directory. Outputs never overwrite existing reports/policies.

```powershell
.\.venv\Scripts\python.exe -m models.image_deepfake.evaluation.benchmark --manifest data/validation.json --purpose validation --output outputs/vit-version-1/validation.json
.\.venv\Scripts\python.exe -m models.image_deepfake.evaluation.select_policy --report outputs/vit-version-1/validation.json --output outputs/vit-version-1/candidate.json
$env:IMAGE_VIT_POLICY_FILE = (Resolve-Path outputs/vit-version-1/candidate.json).Path
.\.venv\Scripts\python.exe -m models.image_deepfake.evaluation.benchmark --manifest data/test.json --purpose test --output outputs/vit-version-1/final-test.json
.\.venv\Scripts\python.exe -m models.image_deepfake.evaluation.promote_policy --candidate outputs/vit-version-1/candidate.json --test outputs/vit-version-1/final-test.json --output outputs/vit-version-1/released.json
```

Candidate selection requires matching model/processor identity, at least 1000 independent scored sources per class and at least 90% scoring coverage. Defaults require a Wilson 95% upper bound of at most 1% real-photo false positives and 5% false low-signal decisions on fake images. These are proposed explicit software gates, not current performance claims. Independent final testing requires at least 1000 sources per class, at least 90% accepted coverage, matching policy identity, no known validation overlap and the same error budgets. The required sample size may be larger for a stable operating point or important slices.

Serving refuses an unpromoted candidate; the benchmark explicitly enables candidate evaluation. After reviewing the test report and data limitations, configure `IMAGE_VIT_POLICY_FILE` to `released.json` and restart services. Policy, evaluation and final-test hashes are checked at load time. Model and processor mismatch disables decisions. Hashes prove consistency, not label truth or independent identity provenance. No correctness confidence is fitted or displayed.

## Kaggle GPU fine-tuning

Import `outputs/image-training/TrustNet_ViT_Kaggle.ipynb`, attach `TrustNet-Image-Training-Sources.zip` as a private source dataset and enable GPU/Internet in a fresh session. The notebook initially measures the frozen ViT. `RUN_TRAINING=False` by default; change it only when baseline/data review justifies the experiment.

The historical xhlulu dataset can exercise preparation/training but is not a recent-generator release set. Dataset preparation keeps all original held-out examples, including localization failures, in `policy_test.json`; prepared crop manifests are separate. The training runner checks group/content leakage and flags candidate near duplicates. It requires GPU, seeds runs, preserves the original binary head while normalizing label order, selects the best validation-loss checkpoint and evaluates the untouched crop test afterward. Head-only and full tuning are separate experiments. Crop-only test metrics do not replace end-to-end testing.

The produced candidate uses safetensors, a processor/config contract and data/report hashes. Installation validates local model files and never activates or overwrites a version:

```powershell
.\.venv\Scripts\python.exe scripts/setup/install-image-vit.py --package C:\path\TrustNet-ViT-Candidate.zip --target models/image_deepfake/trained/vit-candidate-1
$env:IMAGE_VIT_MODEL_DIR = (Resolve-Path models/image_deepfake/trained/vit-candidate-1).Path
```

Use that directory for evaluation, then repeat independent policy selection/test gates with the candidate's own revision. Keep optimizer state separately if needed; it is not installed in serving. No training or Kaggle execution occurred during this software implementation.

## Rollback and monitoring

Keep prior model and policy directories. Restore their `IMAGE_VIT_MODEL_DIR` / `IMAGE_VIT_POLICY_FILE` settings and restart. Remove both settings to return to the pinned baseline with review-only decisions. `IMAGE_ASSESSMENT_POLICY=image-screening-v2` explicitly restores the earlier CNN policy and its artifact requirements.

For approved labeled test inputs, compare saved baseline and candidate evaluation reports before promotion. Review unsupported/failure/abstention rates, per-source false positives/negatives, latency and score shifts. Do not infer accuracy changes from unlabeled score drift. Production image retention or automatic collection has not been introduced. New verified labels are required for ongoing accuracy monitoring.
