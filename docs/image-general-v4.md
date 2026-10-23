# Whole-image Hugging Face screening: implementation and operations

Implemented 23 October 2026. The existing original UI is preserved. This is an experimental screening integration, not independently established detection accuracy.

## Implemented phases

1. Reproduced the hovercar false-face problem. Replaced serving-time Haar proposals with hash-verified, pinned YuNet plus landmark geometry checks. Hovercar: zero faces; earlier portrait: one face. Legacy training localization remains available for compatibility. Existing face policy needs revalidation after changing localization.
2. Added explicit local/hosted whole-image inference, strict label contracts, pinned local model/processor identity, bounded provider retries, sanitized error codes, upload acknowledgement and no silent model fallback.
3. Added image-general-v4. Whole-image inference operates without faces; optional face diagnostics and editable metadata do not vote. The default remains image-vit-v3. No .env secrets or active policy were changed.
4. Added independent validation, threshold selection and final-test promotion commands. Unvalidated policies remain review-required, even with a high model score. Hosted unpinned execution cannot inherit a pinned local policy.
5. Corrected dashboard/report/PDF assessment semantics, missing scores, skipped analyzer observations, actual source SHA256 and unsupported certification claims.
6. Verified 166 image/model/service tests, frontend build/lint, report helper/export checks, local inference and a browser report fixture. The browser fixture uses an actual local inference response; it does not establish a signed-in end-to-end upload flow or production accuracy.

## Observed results and release gates

- Actual hovercar local v4 run: 99.98/100 whole-image AI signal, zero faces, review required because no independent decision policy is validated. This one known example is not an accuracy benchmark.
- Default candidate: Ateeqq/ai-vs-human-image-detector at revision 60e82406916921b823616bee33397baab38af3f0. Its model card reports overfitting concerns. Local processor SHA256: 2bae674efdd7389c7d01ec9f12ebe3b958b52ec64b855f44a614cd60200bf9d5.
- A hosted synthetic-gradient probe returned PROVIDER_BILLING_REQUIRED (HTTP 402). No user image was uploaded. A key being present does not establish usable provider access. Billing/provider availability must be resolved before hosted activation.
- No recent independently labeled validation/final-test dataset is available. Definitive verdict release remains blocked on that evidence. No CNN training is necessary to run this pretrained candidate, but using a pretrained model does not validate its performance.
- Organika/sdxl-detector is optional, SDXL-specific and noncommercial; explicit license acknowledgement is required before selecting it.

## Run the local candidate

From the project root in PowerShell, set process environment variables before starting/restarting the image service:

```powershell
$env:IMAGE_ASSESSMENT_POLICY = 'image-general-v4'
$env:IMAGE_INFERENCE_BACKEND = 'local'
$env:HF_GENERAL_IMAGE_MODEL = 'Ateeqq/ai-vs-human-image-detector'
$env:HF_GENERAL_IMAGE_REVISION = '60e82406916921b823616bee33397baab38af3f0'
$env:IMAGE_GENERAL_POLICY_FILE = ''
.venv/Scripts/python.exe scripts/checks/verify-general-image.py
```

The first local model load needs public Hugging Face downloads; subsequent runs can use the cache. Local readiness does not send image bytes externally. An empty policy file deliberately leaves results review-required. These process variables are inherited only by services started from that shell; restart any existing image worker/service through the normal project startup workflow.

## Hosted configuration

Only after provider access is working, configure IMAGE_INFERENCE_BACKEND=hosted, IMAGE_ALLOW_HOSTED_INFERENCE=true and IMAGE_HOSTED_UPLOAD_ACK=true in the server environment. HUGGINGFACE_API_KEY stays server-side. This sends uploaded image bytes to Hugging Face/provider inference. Leave both upload flags false for local-only operation. A synthetic connectivity test is available:

```powershell
.venv/Scripts/python.exe scripts/checks/verify-general-image.py --probe-synthetic
```

No constructor/readiness probe automatically performs billable image inference. Authentication, billing, rate limit, timeout and malformed-result failures remain unavailable rather than becoming a fabricated safe score.

## Validation and promotion

Use manifests following evaluation/benchmark.py's existing schema: path,label,group,split with optional source/generator/task/pose/quality and subject_id. Labels: 0 real, 1 AI/fake. Supply validation and test splits with independent source groups and no known file, pixel, group or subject overlap. Include recent generators, ordinary camera photos, screenshots, artwork, JPEG and resize conditions. Inspect data provenance and upstream training overlap separately.

```powershell
.venv/Scripts/python.exe -m models.image_deepfake.evaluation.general evaluate --manifest validation.csv --purpose validation --robustness --output outputs/image-validation/validation.json
.venv/Scripts/python.exe -m models.image_deepfake.evaluation.general select --report outputs/image-validation/validation.json --output outputs/image-validation/candidate.json
.venv/Scripts/python.exe -m models.image_deepfake.evaluation.general evaluate --manifest test.csv --purpose test --robustness --output outputs/image-validation/final-test.json
.venv/Scripts/python.exe -m models.image_deepfake.evaluation.general promote --candidate outputs/image-validation/candidate.json --test outputs/image-validation/final-test.json --output outputs/image-validation/released.json
```

Keep all artifacts together. Selection requires at least 1000 independently scored sources per class, 90% accepted coverage, and Wilson 95% upper error bounds of at most 1% real false positives and 5% fake false-low. Final test must independently pass those gates. Hash/model/processor/localizer mismatches invalidate a policy. Output files are exclusive-create to preserve evidence; use a new version directory for another run. Only after review of successful evidence set IMAGE_GENERAL_POLICY_FILE to the released JSON absolute path and restart the service.

## Rollback

Set IMAGE_ASSESSMENT_POLICY=image-vit-v3, clear IMAGE_GENERAL_POLICY_FILE, disable both hosted upload flags and restart the image service. This restores the face-policy route, not a claim of general-image support. No schema migration is required.

## Verification artifacts

Local diagnostic response: runtime_state/image-general-v4/hovercar.json. Synthetic provider result: runtime_state/image-general-v4/hosted-synthetic-probe.json. PDF regression export: runtime_state/image-module-audit/report-v4.pdf. Browser screenshot: outputs/image-remediation/Report-Verification.png. Runtime artifacts are diagnostic and may be ignored by Git; no private source images or credentials are added to the repository.
