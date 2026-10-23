# ViT v3 implementation status

20 October 2026. Implements the software work in `docs/image-detection-audit-and-plan.md`. Current operations and exact commands: `docs/image-vit-v3.md`.

## Delivered

| Phase | Software delivered | Evidence still required |
|---|---|---|
| 0: Baseline | Sanitized runtime/model/processor capture, fixed scope and private portrait regression trace | Representative labeled baseline dataset |
| 1: Contract | Default local ViT-only policy, explicit legacy v2 rollback, scope routing, no CNN prerequisite, distinct model readiness and decision validation, per-view provenance | Broader localization and runtime performance measurements |
| 2: Evaluation | ViT-direct and full-policy runners, source/subject/duplicate audits, failed-input denominators, slices, grouped intervals and derived robustness tests | Licensed recent real/AI examples and independent source/generator holdouts |
| 3: Selection | Annotated localization evaluator, paired crop/padding experiment, validation-only boundary selection and independent final-test promotion gates | Actual annotations, crop comparison, selected operating point and final-test evidence |
| 4: Fine-tuning | Separate GPU ViT notebook, seeded head-only/full tuning runner, strict candidate artifact contract and non-overwriting installer | No GPU training run or candidate checkpoint produced; training remains conditional on baseline/data review |
| 5: Product | API/status, trust/history, report and PDF integration; absent scores are unavailable rather than reassuring zeroes | A complete running gateway/database/browser upload exercise and real-device coverage remain separate from the checks below |
| 6: Promotion | Immutable hashes, evaluation checks, version-directory installation, promotion gate and rollback instructions | No model/policy promoted; ongoing accuracy monitoring requires fresh verified labels |

The user confirmed that no recent labeled dataset is currently available. This implementation therefore does not claim improved modern-generator accuracy, calibrated confidence or completed scientific validation. The older GAN dataset and the EfficientNet notebook remain optional historical experiments, distinct from the existing ViT.

## Verified behavior

An authenticated in-process image-service upload of the supplied portrait returned HTTP 200, status SUCCESS, face fake score **91.35/100**, diagnostic full-frame score **0.09/100**, no missing required checks and verdict UNCERTAIN. `/ready` returned 200 with the pinned ViT and localization loaded and `decision_policy_validated=false`. The missing CNN no longer causes uncertainty. Uncertainty now explicitly reflects the absence of a validated operating point.

A plain no-face image returned UNSUPPORTED with `score_available=false`. The classifier was skipped. Browser verification showed “NO ASSESSABLE FACE” and unavailable scores. Persistence/trust regression tests verify null trust scores for this case. Numeric detector fields retain transport placeholders because the existing shared schema requires numbers; the metadata and display contract prevent treating them as measured scores.

## Verification results

- Image module, image service, gateway, scan-management and image trust-fusion suite: **170 passed in 74.16 seconds**.
- After a final worker-failure metadata correction, the entire image-service suite was rerun: **15 passed in 12.15 seconds**.
- Final frontend production build and lint passed. Image assessment/verdict checks passed, including v3 scope and review behavior.
- Actual PDF export assertions passed using the portrait response, preserving input SHA-256, face/frame scores and uncalibrated policy wording.
- Browser report component was checked with the real API result and the no-face result. This was a local report harness, not a claim of a complete deployed stack or real-device test.
- Both notebook code-cell syntax checks passed. All **65** packaged source hashes match current files; Python sources compile. The source archive excludes credentials, user images and weights. Dependencies and diff whitespace checks passed.
- The temporary preview server, browser tab and frontend fixtures were removed. No unrelated project processes were stopped.

## Handoff

Use `outputs/image-training/TrustNet_ViT_Kaggle.ipynb` with `TrustNet-Image-Training-Sources.zip`. The GPU notebook starts with frozen-model evaluation; fine-tuning is disabled until explicitly selected after data review. It has not been executed on Kaggle. Keep the prior EfficientNet notebook identified as a separate experiment.

Restart existing image/scan processes to load the new default policy, then rescan historical images. Without promoted validation evidence, results remain review-required; changing architecture or lowering a threshold does not establish accuracy.
