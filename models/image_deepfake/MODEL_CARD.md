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

## Installation

Use `scripts/setup/install-image.py` and `scripts/setup/install-image-localizer.py`. They pin source versions and verify artifact checksums. A teammate does not need the author's Hugging Face cache. See the root README for service startup and optional research-localizer restrictions.
