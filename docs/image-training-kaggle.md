> This document describes the optional EfficientNet experiment. For the existing ViT and its separate notebook, use [ViT v3 operations](image-vit-v3.md).

# Kaggle GPU training handoff

## Files

- `outputs/image-training/TrustNet_Image_Kaggle_Training.ipynb`
- `outputs/image-training/TrustNet-Image-Training-Sources.zip`
- `outputs/image-training/SHA256SUMS.txt`

The source archive is generated from an explicit allowlist. It contains no .env, credentials, training data, user images, checkpoints or private project attachments. The notebook verifies the packaged source hashes. Regenerate it after image-code changes:

```powershell
.\.venv\Scripts\python.exe scripts/packaging/package-image-training.py
```

## Run

1. Create a private Kaggle notebook and import the supplied `.ipynb`.
2. Upload the source ZIP as a private Kaggle dataset and attach it to the notebook.
3. Attach `xhlulu/140k-real-and-fake-faces`, version 2: https://www.kaggle.com/datasets/xhlulu/140k-real-and-fake-faces .
4. Select a GPU accelerator and enable Internet. Start a fresh session so the tested OpenCV package is loaded correctly. Keep Kaggle's GPU PyTorch/torchvision installation.
5. Run the cells. Inspect retained/excluded counts before training. Face preparation is CPU work across many images and may take substantial time. Training has a 20-epoch maximum with validation early stopping.
6. Review held-out CNN metrics and the separate serving-policy sample report, including abstention and failures. These are GAN-face benchmark results, not general AI-image accuracy.
7. Save the notebook version with outputs. Download `TrustNet-Image-Trained-Artifact.zip`; retain `training_state.pt` separately if optimizer-state recovery is needed.

The notebook is syntax-checked and its source bundle is verified locally. It has not been executed on Kaggle in this task. Kaggle account access, GPU eligibility and session limits remain controlled by Kaggle; this workflow does not bypass them. The real-face dataset has no verified subject identities; source-image hashes are not claimed as identity separation. Preserve upstream FFHQ and fake-face licensing/attribution information.

## Install locally

```powershell
.\.venv\Scripts\python.exe scripts/setup/install-image-model.py --package "C:\path\TrustNet-Image-Trained-Artifact.zip"
```

The installer validates the artifact before activation and refuses to overwrite existing model directories. For a new version:

```powershell
.\.venv\Scripts\python.exe scripts/setup/install-image-model.py --package "C:\path\TrustNet-Image-Trained-Artifact.zip" --target models/image_deepfake/trained/version-2
```

Set `IMAGE_MODEL_DIR` to that version directory, restart image and scan services, and run `scripts/checks/verify-image-model.py`. `/ready` must return 200. Preserve the prior version for rollback. A readiness pass proves artifact/runtime compatibility, not accuracy or confidence calibration. Rescan historical images after deployment.
