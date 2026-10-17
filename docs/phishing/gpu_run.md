# Full BERT GPU run

User selected preparing the full run for a GPU machine on 12 October 2026. Local CUDA is unavailable. This package contains the full immutable prepared dataset, frozen splits, pretrained BERT source, trained LightGBM branch, and runnable training/fusion/evaluation code. A pretrained encoder with a newly initialized head is not a phishing classifier.

Extract `exports/phishing-gpu.zip` on a CUDA machine. Verify files against GPU_PACKAGE_MANIFEST.json. Create a Python 3.11 virtual environment and install `services/phishing_url/requirements.lock`; install a CUDA-compatible PyTorch wheel for the machine if necessary. Record any version change and rerun the suite. The lock records the local environment; GPU driver/CUDA compatibility must be verified on the destination.

From package root run `bash scripts/train-phishing-gpu.sh`. It asserts CUDA, fine-tunes all 360,066 training rows for up to three epochs, selects checkpoints using validation domains with sha256 mod 3=0, predicts all validation rows, tunes weighted voting on partition 0, calibrates on partition 1, selects thresholds on partition 2, builds a checked hybrid and evaluates the untouched test set once. No source URL is fetched during training.

Return `models/phishing_url/checkpoints/hybrid/` and `models/phishing_url/research/hybrid_test.json` to this branch's checkout. Set PHISHING_MODEL_MANIFEST to hybrid/manifest.json. Update the model card and promotion decision with actual component, hybrid, calibration and latency results. If the hybrid does not improve the baseline at the agreed operating point, report that result instead of promoting by architecture alone.

Calibration and threshold data remain domain-isolated from training and test. Source lineage and temporal/campaign generalization remain unmeasured. Nearly all source URLs lack a scheme; assumed HTTP is parsing provenance, not observed transport. The current LightGBM branch is lexical; WHOIS/TLS features are observed separately and not used by this artifact. An enriched variant requires historical-label/collection parity and independent training/evaluation.

GNN remains the plan's later upgrade, not part of this two-branch milestone.

## Commands on a Linux CUDA machine

Copy the ZIP to the GPU machine, extract it into a new directory, and open a terminal there. Then:

```bash
python3.11 -m venv .venv-gpu
source .venv-gpu/bin/activate
python -m pip install -r services/phishing_url/requirements.lock
python -c "import torch; print(torch.cuda.get_device_name(0)); assert torch.cuda.is_available()"
bash scripts/train-phishing-gpu.sh
```

If the CUDA check fails, install the PyTorch wheel compatible with that machine's driver before running training. Record changes to dependency versions. Keep package paths intact: commands run from extracted package root. The run uses all training rows; it may take hours and prints training progress. Final test evaluation is also substantial. The package does not submit a cloud job or contain cloud credentials.

Return the complete `models/phishing_url/checkpoints/hybrid` directory and `models/phishing_url/research/hybrid_test.json`. Review metrics before switching the worker. For local operation use `./scripts/start-phishing.ps1 -Manifest models/phishing_url/checkpoints/hybrid/manifest.json -Kafka` in an environment with BERT dependencies, or the documented Compose hybrid override. Do not start a second worker on port 8007 while the baseline container is running.
