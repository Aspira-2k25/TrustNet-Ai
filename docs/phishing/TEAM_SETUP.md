# Phishing setup

The canonical setup guide is [TEAM_SETUP.md](../TEAM_SETUP.md). Do not switch branches or replace your existing `.env` just to install weights.

Put `TrustNet-Phishing-regional-recall-v1.zip` in `exports/`, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts/setup/install-phishing.ps1
.\start-dev.bat
```

The selected release is `regional-recall-v1`; all eight artifacts are verified against the pinned manifest. Existing image/scam environments are preserved. Pulling Git alone does not install model weights.
