#!/usr/bin/env bash
set -euo pipefail
# Run from repository root with prepared dataset + pinned pretrained source copied.
python -c 'import torch; assert torch.cuda.is_available(), "CUDA GPU required for this full run"'
python -m models.phishing_url.training.train_bert models/phishing_url/data/primary/prepared/prepared.csv models/phishing_url/data/bert_source models/phishing_url/checkpoints/bert --epochs 3 --batch-size 16
python -m models.phishing_url.training.tune_ensemble models/phishing_url/checkpoints/lightgbm/validation_predictions.csv models/phishing_url/checkpoints/bert/validation_predictions.csv models/phishing_url/checkpoints/fusion
python -m models.phishing_url.training.build_bundle models/phishing_url/checkpoints/lightgbm models/phishing_url/checkpoints/bert models/phishing_url/checkpoints/fusion models/phishing_url/checkpoints/hybrid
python -m models.phishing_url.evaluation.evaluate models/phishing_url/data/primary/prepared/prepared.csv models/phishing_url/checkpoints/hybrid/manifest.json models/phishing_url/research/hybrid_test.json
