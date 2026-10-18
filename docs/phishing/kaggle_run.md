# Kaggle GPU training

Use refreshed phishing-gpu.zip with Phishing_Kaggle.ipynb. Create a private dataset by uploading the ZIP (Kaggle extracts its contents), attach it to the notebook, choose a GPU accelerator, and enable Internet for dependency installation. Keep the dataset/notebook private. Account verification may be required for GPU access; follow Kaggle's UI and displayed quota.

The trainer prints epoch/batch/training percentage and writes progress.json. Every 500 batches and after each validated epoch it atomically saves resume.pt containing model/optimizer/RNG state and dataset/configuration signature. Resume rejects different dataset hashes, batch sizes or epoch settings. At most the work after the last saved checkpoint must be repeated. Validation/test work is separate from training percentage.

Kaggle /kaggle/working is not a permanent checkpoint store unless outputs are saved/downloaded. Before session termination, preserve the complete bert output directory (including resume.pt and best-model bert subdirectory) through normal notebook output/download controls. Attach preserved outputs as a private input on a later session and set RESUME_FOLDER to the directory containing resume.pt. The workflow does not bypass quotas or guarantee session availability. Old Colab model weights alone do not resume optimizer/batch state.

After successful completion, download phishing-trained-results.zip and the saved training outputs. Verify hybrid test metrics before deployment. This notebook has been generated and checked locally; no Kaggle GPU training result is claimed.
