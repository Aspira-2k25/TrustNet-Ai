# Image evidence model card

## Runtime components

Global AI classification uses `buildborderless/CommunityForensics-DeepfakeDet-ViT`, revision `ac6ee457bea904a373065754107451793b56db00`, MIT licence. Its single fake logit is converted with sigmoid, rather than interpreting a one-output model with softmax. The processor creates the documented classifier view; the original upload bytes remain available for native-resolution localization and hashing.

An experimental standardized 384-dimensional CLS feature head uses logistic regression. It was fitted on 96 training images, with 48 validation and 48 held-out test images. SafeIMG generated images carry CC BY-NC-SA 4.0 terms and underlying COCO real-image rights apply. This adaptation is research material, not an unrestricted commercial model release. The head failed a separate high-resolution real-photo guard, with four false alerts among eight photos. It cannot independently trigger an AI-generated verdict.

TruFor supplies genuine per-pixel localization, with official source revision `ae54475df6f41a491d7615100feb19263dec13f7`. Its licence restricts use to nonprofit/informational purposes and excludes unrestricted commercial or industrial use. It is optional and isolated behind the localizer interface. Set `IMAGE_LOCALIZER_BACKEND=none` to disable it. Disabling it does not provide an alternative localizer or establish authenticity.

Provenance checks inspect metadata and available C2PA claims. Missing metadata is neutral. Editable software tags are observations, not proof. Quality checks report resolution, compression and processing limits.

## Original data and outputs

Accepted images are JPEG, PNG and WebP, with a 10 MB upload limit, minimum dimension 32 pixels and maximum 24 megapixels. Animated images are rejected. Source SHA-256 and native dimensions are recorded. Native pixels or overlapping tiles feed TruFor; partial or timed-out localization is discarded. Overlays, masks and raw maps are saved privately with the original image and require scan-owner authentication.

Only the native JPEG localization profile has validated decision thresholds. PNG and tiled outputs are diagnostic evidence and do not establish supported manipulation regions. ELA brightness and model attention are not edit masks.

Classical supporting diagnostics include JPEG-only recompression differences (ELA), high-pass noise residual statistics and ORB self-matching with RANSAC for repeated-pattern candidates. They run on at most a 768 by 768 native central window, with its coordinates and coverage recorded. Original pixels are not resized for these checks. ELA uses JPEG quality 90 and a fixed 8x display gain, not a fitted detection threshold. It is unavailable for PNG and WebP. Texture and naturally repeated objects can trigger these observations. They produce no calibrated AI/manipulation probability, no supported edit regions and no input to the verdict. Their private ELA view and plain-language observations appear in the report; the PDF includes their scope and limitations. The prior face, scene, eye-reflection, watermark and other hand-weighted heuristics have not been reinstated as detection evidence.

Optional Grad-CAM differentiates the selected ViT AI logit at the final block's pre-attention normalization layer. Its map is shown on the classifier's resized/cropped view, with explicit dimensions. It is model attention, not native-pixel manipulation localization or proof of AI. The image form enables it by default and allows opting out of the additional computation. Explanation failures do not change the verdict. Gradients are not accumulated on parameters and hooks are removed after each request. ELA, noise and copy-move analyzers have separate modules under `forensics/`; classifier explanations live under `explainability/`.

## Decisions and boundaries

The versioned policy is `calibration/evidence-v2.json`. Its fitted boundaries belong to the recorded validation cohorts, not universal probabilities. The primary AI raw-score guard is 0.3546251223812103. The experimental head guard is 0.8507126739067924, with primary-model corroboration required. The native JPEG manipulation raw guard is 0.9443824291229249; the pixel threshold is 0.99, minimum reliability 0.25 and minimum component area fraction 0.001. The complete policy, processing budgets and calibration limitations are in that configuration.

Authenticity decisions are currently disabled. Low AI or manipulation readings do not prove a real photograph. Weak evidence, conflicting evidence or unsupported edit types produce Inconclusive. This is a deliberate coverage restriction, not an accuracy improvement claim.

## Measured evidence

The portable split manifest is `benchmark/manifests/image-head-splits.json`. Exact hashes and source families were checked across training, validation and test. The fresh OpenAI diagnostic image and its variants were excluded from head training and threshold fitting, but informed development and are not an independent test. Upstream pretraining and generator-batch overlap are not fully known.

The 32-image actual-pipeline comparison contains 16 real and 16 generated images. AI alert recall increased from 0/16 to 6/16. False alerts were 0/16 in both versions. Inconclusive share increased from 12.5% to 81.25%. These small-cohort results do not establish broad generator accuracy.

Among 300 additional unique COCO real-photo sources, three false alerts were observed: 1.0%, with 95% Wilson interval 0.34% to 2.90%. Inconclusive share was 99%. The upper confidence bound exceeds 2%; a population FPR below 2% has not been demonstrated. Compression, filters, screenshots and low-light variants are software proxies. DSLR, actual social-app processing and device beauty modes are not comprehensively verified.

Native JPEG synthetic splice/copy-move testing detected regions in 29/32 edited images, with mean IoU 0.6979 including misses as zero. One of 64 real images had a false region alert. Other challenges were weak: GLIDE inpainting supported regions 0/20, face-swap detection 1/20 with no ground-truth masks for IoU, and rectangular content-aware removal proxies 3/12 with mean IoU 0.0737. These results do not establish modern generative-fill or semantic object-removal support.

Aggregate results are in `benchmark/results/reference-evaluation.json`. Raw research data stays outside the application and is not needed for runtime. These results are probabilistic indicators, not proof of image origin or editing.

## Expanded head experiment, October 2026

One new linear head was trained on frozen ViT features using 2,089 distinct real files and 2,089 generated files, with two JPEG/resize/blur/noise/filter views per training original. Real sources were COCO (1,494), Open Images (468), RAISE (90) and SIDD (37). Generated training sources were six GenImage generators plus TGIF SDXL. Calibration used 840 separate images and isotonic regression; the threshold used another 832 images. Thirteen duplicate/source-family/perceptual-conflict records were quarantined before fitting. Source and split manifests record exact hashes; cross-split exact-hash overlap was zero. Capture correlations and unknown backbone pretraining overlap remain limitations.

The classifier view was explicitly 224 by 224, including the processor crop override. A preliminary cache that had silently remained at 384 was archived and was not used to fit this candidate. File type and encoded size were matched between classes. A development-only classifier using file size, format and view dimensions had ROC-AUC 0.500. This checks those shortcuts, not every content confound. ArtiFact was not mixed into this run because the examined convenient mirror lacked the generator/edit provenance needed for the split. Local SDXL/Flux generation was not attempted on this CPU-only machine.

FLUX.1-schnell, PixArt-Sigma and SD3 were excluded from this head's fitting, calibration and threshold selection. The threshold was frozen at 0.9803921568627451 before their test inference; threshold-partition real FPR was 4/416 (0.962%). The untouched main test contained 1,008 real and 750 generated images. It was never used to retune the candidate.

| Same 1,758-image AI-stream test | Existing primary boundary | New calibrated head |
| --- | ---: | ---: |
| Generated-image recall | 53.47% | 26.80% |
| Real false alerts | 3/1,008 (0.30%) | 14/1,008 (1.39%) |
| 95% Wilson FPR interval | 0.10% to 0.87% | 0.83% to 2.32% |
| AI-stream Inconclusive share | 77.02% | 87.77% |

Unseen-generator recall was 29.6% versus 14.0% for FLUX, 88.0% versus 44.0% for PixArt, and 42.8% versus 22.4% for SD3, respectively. The new head's supplemental seen-generator recall was 63.83% on 600 generated images. Its binary alarm ROC-AUC was 0.8481, precision 0.9349 and F1 0.4166; these are not four-verdict authenticity accuracy.

**The new head was rejected and is not a runtime dependency.** It reduced recall, increased real false alerts and missed the prespecified upper-confidence-bound guard. Existing weights and decision boundaries were preserved. The requested reduction in abstention has not been achieved.

In a fixed 48-image paired full-pipeline subset, the current policy produced 81.25% Inconclusive versus 91.67% for the rejected candidate. Generated-image recall was 8/24 versus 3/24. Both produced one real false alert among 24 real images: 4.17%, with a wide 95% interval of 0.74% to 20.24%. This small source-stratified subset does not establish population FPR. The larger 1,008-real measurement above covers the AI stream, not every full-pipeline branch. A whole-system FPR below 2% has not been established.

TruFor was also evaluated on aligned operation masks for 20 TGIF partial edits. Photoshop/Firefly: detected 6/10, missed 4/10, mean IoU 0.1101. SD2: detected 3/10, missed 7/10 including three CPU-budget timeouts, mean IoU 0.0534. IoU includes missed/unavailable cases as zero. These are raw diagnostic detections on a small ordered sample; production-supported PNG/tiled detections remain zero. Masks describe editing operations, not verified synthesized pixels. These results do not justify enabling inpainting support or authenticity.

Compact evidence is retained in `benchmark/results/reference-evaluation.json`. Full manifests, rejected artifacts and substantial outputs stay outside the runtime repository. Research sources retain their own terms, including noncommercial/research restrictions. No broad GPT-image, Gemini or all-generator detection claim follows from this experiment.

## CPU runtime and native-crop experiment status, 21 October 2026

The deployed classifier, feature-head weights and decision boundaries remain unchanged. The native-crop experiment completed using CommunityForensics and DINOv2, five native 224 pixel crops without resizing source images, and cached features from 5,850 originals plus 1,012 training stress views per backbone. The head was fitted on 2,089 real and 2,089 generated training images, with separate 840-image calibration and 832-image threshold partitions. The selected development option was the fixed primary/native-head mean followed by isotonic mapping. Its threshold was frozen before fresh test inference. Full OpenCLIP extraction was skipped because the source-shortcut audit failed; its 40-image pilot cache remains external.

The fresh-image diagnostic contained 668 COCO real photographs and 441 generated images. Entire FLUX, PixArt and SD3 generator identities were excluded from this head's training/calibration/threshold selection, but these generators had been examined in an earlier experiment. Original image identities were screened against prior sources before outcomes were extracted. Unknown upstream pretraining and batch/semantic overlap remain. This is not an all-generator or device-diversity certification.

| Same 1,109-image AI-stream test | Existing primary boundary | Native-crop candidate |
| --- | ---: | ---: |
| Generated-image recall | 400/441, 90.70% | 394/441, 89.34% |
| Real false alerts | 1/668, 0.15% | 1/668, 0.15% |
| 95% Wilson real-FPR interval | 0.026% to 0.843% | 0.026% to 0.843% |
| Binary accuracy | 96.21% | 95.67% |
| Precision | 99.75% | 99.75% |
| F1 | 95.01% | 94.26% |
| ROC-AUC | 0.9988 | 0.9816 |
| AI-stream no-alert/uncertain share | 63.84% | 64.38% |

Binary accuracy/F1 treat no alert as negative for evaluation; runtime no-alert results do not authenticate real photographs. The uncertain share above is AI-stream-only and cannot be compared directly with the earlier 81.25% full-pipeline subset. Nor can the unchanged primary's higher recall on this different collection be called a software improvement.

Generator recall, existing versus candidate: FLUX 118/146 (80.82%) versus 110/146 (75.34%); PixArt 146/146 (100%) for both; SD3 136/149 (91.28%) versus 138/149 (92.62%). **The candidate was rejected and was not installed.** It lost six generated-image detections overall, did not reduce abstention, and retained an unresolved source-metadata confound. No test-driven retuning or further long experiment was started. Full-pipeline false-positive certification, GPT-image/Imagen coverage and reliable inpainting localization remain unresolved.

Test manifest SHA-256: `88bf57220af692c1cf4d0ff8ff1aa2edd55bd0a34fe4b815e95d463ce3a32447`. Candidate canonical-content SHA-256: `85d7d39ceb3ad5448c8b81fccd467d7f36e8310599c1a00873c5053552333b0b`. Full caches and rejected artifacts stay outside the runtime repository; compact aggregate results are in the existing reference-evaluation JSON.

A source-metadata control fitted on the training partition and evaluated on the separate calibration partition reached ROC-AUC **1.00**, using original width, height, file bytes and JPEG format. This fails the near-chance shortcut target. These fields are not direct native-crop model inputs, but fixed crop dimensions do not rule out source content or compression-history confounds. The report explicitly blocks promotion pending a controlled-input audit and the independent whole-pipeline real-photo guard. Neither extraction completion nor a strong candidate score establishes a valid improvement.

TruFor now runs in a resident, killable CPU worker with a 20 second request boundary. Cold startup is allowed up to 90 seconds before accepting requests; a 30 second startup budget was observed to disable the localizer under concurrent CPU research load. This startup allowance does not extend scan inference budgets. Two previously slow TGIF cases changed from 75.27 and 68.48 seconds to 21.53 and 21.44 seconds respectively, returning partial, uncertain assessments without partial masks. This bounds latency; it does not improve localization recall or IoU. A three-request public COCO image check measured p50 8.64 seconds and p95 9.94 seconds; message and quick URL checks measured p50/p95 0.32/0.84 and 0.018/0.032 seconds respectively. These small developer-load measurements are not a deployment SLA or broad latency distribution.

Grad-CAM maps are projected through the actual classifier resize and center-crop geometry back to the original aspect ratio; unviewed borders remain unchanged. A 12-image diagnostic deletion check measured mean AI-score drops of 0.00268 for highlighted cells and 0.00124 for fixed random cells, with highlighted deletion larger in 7/12 cases. This is limited attention evidence, not manipulation ground truth or a claim of universal explanation faithfulness.

## Installation and distribution

Use `scripts/setup/install-image.py` and `scripts/setup/install-image-localizer.py`. They pin source versions and verify artifact checksums. A teammate does not need the author's Hugging Face cache. See the root README for service startup and optional research-localizer restrictions.
