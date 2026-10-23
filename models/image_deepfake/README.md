# Image screening module

The default `image-vit-v3` policy uses the existing pinned local face ViT. It does not require a CNN. Full-frame results are diagnostic; detected-face scores and coverage are explicit. Readiness does not imply validated thresholds or accuracy. Until independent policy-validation and final-test gates pass, verdicts remain review-required.

See [current operations](../../docs/image-vit-v3.md), [audit and plan](../../docs/image-detection-audit-and-plan.md), and [historical v2 reference](../../docs/image-screening.md). Input security and advisory forensic observations remain enabled. Scores are not calibrated correctness probabilities.

Use `evaluation.benchmark` for ViT-only and end-to-end testing. Training on Kaggle is conditional on data and baseline review. No recent labeled dataset is currently supplied, and no modern-generator accuracy is claimed. The optional EfficientNet training path remains separate.

The optional `image-general-v4` integration screens whole images using an explicitly selected pretrained Hugging Face backend. See [implementation, activation and remaining release gates](../../docs/image-general-v4.md). It is not activated by default, and its scores remain review-required until independent validation and final-test gates pass.
