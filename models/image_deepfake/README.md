# Image Deepfake Model Package (models/image_deepfake)

Reusable model and forensic pipeline package used by backend services.

## Scope

This package contains detector logic, forensic analyzers, preprocessing, explainability, and tests.

## Directory Overview

- `inference/` - detector entrypoints and model clients
- `forensics/` - signal analyzers (FFT, ELA, noise, metadata, face/physics, etc.)
- `preprocessing/` - input normalization and transforms
- `evaluation/` - evaluation utilities
- `training/` - training-related scripts/assets
- `tests/` - package tests

## Core Detector

`inference/efficientnet_detector.py` orchestrates multi-signal inference and produces `DetectionResult` objects compatible with shared schemas.

## Install And Use In Development

```bash
pip install -r models/image_deepfake/requirements.txt
pip install -e shared/
pip install -e models/image_deepfake/
```

## Run Tests

```bash
python -m pytest models/image_deepfake/tests -v
```
