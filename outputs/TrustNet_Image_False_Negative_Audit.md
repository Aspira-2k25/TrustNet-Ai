# TrustNet AI image false-negative audit

## Outcome

The supplied image reproduces the screenshot exactly: **8.1/100 risk**, **88% heuristic confidence**, backend verdict **AUTHENTIC**, and two reported faces. The website displays the backend result as **LOW MANIPULATION SIGNAL**. Taking the user's stated AI-generated origin as the supplied ground truth, this is a reproduced false negative.

The strongest finding is an input-path problem. The same cached classifier returns **99.9097% Real** on the full image but **95.9193% Fake** on a manually isolated crop of the actual face. In a diagnostic run that changes only the classifier input to that crop, the complete detector returns **81.53/100** and **LIKELY_AI_MANIPULATED**. The normal pipeline never sends detected face crops to the classifier.

This diagnostic establishes a specific failure mechanism for this image. It is not a validated replacement cropping policy or an accuracy benchmark.

## Reproduction boundary

- Input: 1106 x 1422 JPEG, 325615 bytes.
- SHA-256: `4b20251f1ff45f11f9b7bbead557a848e32f40a306dd0a71ca57c6b92fb0f91e`.
- Model: `dima806/deepfake_vs_real_image_detection`, cached locally.
- Raw model labels: `0 = Real`, `1 = Fake`.
- Model preprocessing: resize to 224 x 224, configured rescaling and normalization.
- Hosted inference was forced unconfigured. All user-image inference ran locally with offline model loading.
- Optional vision reasoning was disabled, matching the screenshot's fast-analysis path. Grad-CAM evidence generation was disabled; the classifier, forensic and risk paths ran.
- No application source, thresholds, model weights, running services or user databases were changed.

## Findings

### 1. The classifier processes the full portrait instead of the face

`LocalViTDeepfakeDetector.predict` opens the complete image and calls `pipe(image)`. Its `has_face` argument does not select or crop a face. The hosting client also submits the whole image in its hosted path. The 1106 x 1422 scene is resized to 224 x 224, changing the subject scale and surrounding visual context.

Measured raw outputs:

| Classifier input | Fake output | Real output |
| --- | ---: | ---: |
| Full original image | 0.0903% | 99.9097% |
| Mirrored full image | 0.0973% | 99.9027% |
| Manual face crop, x=345..820, y=355..875 | 95.9193% | 4.0807% |
| Wider portrait crop, x=260..930, y=180..1050 | 0.0998% | 99.9002% |

The wide portrait crop still fails. This supports strong sensitivity to crop/context/face scale; it does not isolate which of those factors alone causes the change.

Source: `models/image_deepfake/inference/local_vit_detector.py`, `_get_pipeline` and `predict`.

### 2. Face localization is degraded and reports background as faces

The installed runtime reports OpenCV 5.0.0. In this environment, `cv2.CascadeClassifier` is absent and the configured cascade directory contains no XML files. `FaceAnalyzer` catches constructor errors and continues with zero loaded face cascades. The eye-reflection analyzer is also unavailable.

The skin-color distance-transform fallback creates both reported boxes at source line 194:

- `(687, 0, 370, 370)`
- `(476, 0, 322, 322)`

These boxes cover background, upper hair and framed-wall regions rather than the actual face. The resulting low boundary score, **0.097**, therefore measures the wrong regions. Nevertheless, the result claims natural facial texture across two faces.

The annotated evidence image is saved at:
`C:\Users\papoo\OneDrive\Documents\TrustNet-Ai\runtime_state\image-audit\face-boxes.png`

Source: `models/image_deepfake/forensics/face_analyzer.py:37`, `:40`, `:143`, `:194`, `:309`; `models/image_deepfake/forensics/physics_eye_reflection_analyzer.py:24`.

Fixing localization alone will not correct the classifier input: the classifier currently ignores those boxes. Both runtime capability checks and the face-to-classifier path require attention.

### 3. Weak forensic measurements are presented as verified camera evidence

The run produces zero strong physical domains. Several checks therefore fail to challenge the mistaken full-image classifier result:

| Signal | Recorded result |
| --- | --- |
| Frequency | score 0.075; no synthetic-pattern flag |
| Pixel/CFA proxy | score 0.35; CFA residual 7.32 |
| Micro-jitter | kurtosis 16.23, above configured 7.0 threshold |
| Patch variability | ratio 2.04, above configured 0.95 threshold |
| Noise | score 0.05; residual standard deviation 5.52 |
| Face boundary | score 0.097 from incorrect boxes |
| Eye reflection | skipped because cascade processing is unavailable |
| Provenance | no generator marker; EXIF missing |

The pixel analyzer requires a CFA anomaly together with jitter or entropy anomalies. The CFA residual is within its accepted range, so two anomalous measurements still produce `is_morphing_detected=False`. The negative branch then states that natural micro-edge continuity is "verified".

The noise analyzer measures high-pass residual statistics. It does not match a trusted camera sensor fingerprint. The face analyzer measures skin and boundary statistics, not a trained Face X-Ray classifier. Absence of a compositing seam is also insufficient for rejecting a fully generated image.

Source: `models/image_deepfake/forensics/pixel_morphing_analyzer.py:89`, `:93`, `:107`; `models/image_deepfake/forensics/noise_analyzer.py`; `models/image_deepfake/forensics/face_analyzer.py`.

### 4. Score fusion accepts the low signals without an effective uncertainty gate

For this run, the weighted sum is **0.13453** and total weight is **1.66**:

`100 * 0.13453 / 1.66 = 8.104216867...`

Native-score rounding produces the displayed **8.1**. The classifier weight is 0.40, approximately 24.1% of the total weight, not 40% of the normalized result.

An authenticity suppression branch executes when the classifier says real and no secondary physical domain is strong. It caps anomaly at 0.16 and clears contradiction. **That cap does not lower this particular result**, because its initial anomaly is already 0.081042. The audit trace records no change after the weighted average.

Removing only the ViT weight arithmetically would yield approximately **10.65/100**, still low. Therefore, the failure is not explained by classifier weighting alone. The other weak checks also supply low values.

Source: `models/image_deepfake/inference/efficientnet_detector.py:389`, `:528`, `:532`.

### 5. The 88% confidence is a hand-written agreement formula

The detector computes:

`confidence = round(max(0.70, min(0.98, 0.92 - std(active_scores) * 0.35)), 2)`

Measured score spread is **0.1008894934**, resulting in **0.88**. This formula rewards agreement among low-valued signals even when localization is wrong and a relevant analyzer is skipped. It also imposes a 70% minimum within this success path.

The frontend labels this value heuristic, but neither 88% nor the classifier's 99.9% establishes correctness on this image.

Source: `models/image_deepfake/inference/efficientnet_detector.py:619`.

### 6. Explanations overstate what was measured

The backend emits an AUTHENTIC label below risk 22. Its face explanation states that the image is consistent with human photography, natural lens characteristics and consistent lighting. A separate reason reports 99.9% real confidence.

The frontend correctly maps the low score to LOW MANIPULATION SIGNAL and includes a disclaimer. It does not invert the classifier's labels. However, its green presentation and backend-supplied claims still imply verification beyond the measurements. The summary is especially misleading because the face regions are wrong and eye-reflection processing was skipped.

Source: `models/image_deepfake/inference/efficientnet_detector.py:161`, `:619`, `:668`; `frontend/src/services/verdict.ts:16`.

### 7. There is no independent trained EfficientNet deepfake classifier in this path

The detector loads ImageNet EfficientNet-B0, evaluates `self.model.features(tensor)` and records feature variance. It does not use a trained fake/real EfficientNet head to supply a second learned classification. Its own analyzer text states that a deepfake head is pending dedicated training.

Thus the ensemble is not a set of several independently validated AI-image classifiers. Its learned fake/real decision depends on the configured ViT, with heuristic measurements and optional vision reasoning around it.

Source: `models/image_deepfake/inference/efficientnet_detector.py:302`, `:813`, `:816`.

### 8. The upstream model explicitly warns about concept drift

The model author states that its training dataset is several years old and warns that newer generation tools cause concept drift. The author recommends retraining with current labelled data. This supports a broader generalization concern, but the crop experiment is the direct evidence for this specific failure.

Primary source: https://huggingface.co/dima806/deepfake_vs_real_image_detection/raw/main/README.md

Published evaluation numbers on an older dataset do not validate this generated portrait or the application's heuristic fusion. Lowering a raw fake threshold to 0.1 would not catch the full-image output of approximately 0.0009026 anyway. Arbitrarily tuning a threshold for this example would not establish a sound correction.

## Diagnostic pipeline experiment

Only the classifier input was replaced with the manual face crop. Forensic analysis still used the original full image. The result changed to:

- Model Fake index: **95.92**.
- Final risk: **81.53/100**.
- Verdict: **LIKELY_AI_MANIPULATED**.
- Heuristic confidence: **82%**.

This proves that the existing classifier can identify synthetic evidence in this face at a different input scale/context. It does not justify hardcoding this crop or labelling all portraits fake.

## Recommended correction order

1. Add explicit runtime capability checks. Restore a supported face detector and required resources; otherwise report localization unavailable instead of silently calling skin blobs faces.
2. Add a defined face-crop inference path alongside full-frame inference. Preserve crop coordinates and both scores. Treat strong disagreement as uncertainty until the combination policy is validated.
3. Replace authenticity-verification wording with measured observations. Do not claim camera origin from low gradients, clean noise statistics, or absent generator metadata.
4. Separate model score, heuristic index, analyzer availability and confidence. Remove the arbitrary confidence floor from any claim of prediction reliability.
5. Validate on provenance-labelled modern generated portraits and real camera controls, including recompression, resizing, crops and multiple generators. Separate development/calibration data from an untouched test set.
6. Reassess classifier choice and thresholds using those results. A newer model may be needed, but replacing the model alone does not repair broken localization or misleading confidence.

## Evidence files

- `runtime_state/image-audit/audit.json`: exact input identity, full result, raw predictions, model preprocessing and fusion state.
- `runtime_state/image-audit/face-diagnostics.json`: installed OpenCV capability and box-creation path.
- `runtime_state/image-audit/counterfactual.json`: manual face/context crop outputs and weight-removal arithmetic.
- `runtime_state/image-audit/crop-pipeline-counterfactual.json`: diagnostic full-pipeline result using the manual face crop for the classifier only.
- `runtime_state/image-audit/face-boxes.png`: visualization of the actual fallback boxes.

The audit is complete. Application source and model weights remain unchanged. No service was started or stopped for this audit.
