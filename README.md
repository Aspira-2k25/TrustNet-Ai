# TrustNet AI

A web application for image forensics, scam-message assessment and phishing-URL analysis, with authenticated scan history and PDF reports.

## Run locally

Follow the [Team Handoff & Setup Guide](docs/TEAM_HANDOFF_AND_SETUP_GUIDE.md) (or [docs/TEAM_SETUP.md](docs/TEAM_SETUP.md)) for dependencies, model packages, and standalone setup scripts (`setup-phishing.bat` / `setup-scam.bat`). After setup:

```powershell
.\start-dev.bat
```

Open **http://localhost:5173** and sign in with your own TrustNet account. Stop launcher-owned local services with ` .\stop-dev.bat `.

## Implemented analysis

| Module | Current approach | Input / result |
| --- | --- | --- |
| Scam messages | Fine-tuned DistilBERT plus TF-IDF / Logistic Regression; calibrated message-score fusion | SMS or selected email, windowed inference and occlusion highlights |
| Embedded links | The selected phishing detector checks extracted text URLs, HTML destinations and extension-supplied links | Up to eight unique links; per-link results and missing-check coverage |
| Phishing URLs | Checksummed `regional-recall-v1` URL-text/structure experts, routing and bounded rescue; link-forensic rules | URL risk index, reasons and optional isolated live collection |
| Images | Preserved `dima806/deepfake_vs_real_image_detection` ViT and conditional forensic checks | Rule-based risk, evidence, supporting EfficientNet-B0 Grad-CAM |

Message/URL late fusion uses the maximum available risk index and preserves branch scores. A URL alert can escalate the verdict; missing links never count as safe. This combined index is **not calibrated as a probability** and has no measured combined-system accuracy yet. Sender ownership and AI authorship are not verified.

## Runtime structure

```text
frontend/                    React dashboard, history and client-side PDF export
gateway/                     Authenticated FastAPI routing and request limits
services/                    Auth, scan management, scam, phishing, image and trust services
models/                      Inference, preprocessing, selected configs and model installers
extensions/trustnet-mail/     Manifest V3 Gmail adapter and connection settings
scripts/setup/               Installers and module setup helpers
scripts/ops/                 Internal service launch/stop and infrastructure helpers
scripts/checks/              Model verification and service/integration smoke checks
scripts/packaging/           Checksummed model and portable-runtime packaging
scripts/research/            Training, dataset and historical experiment commands
docs/                        Contracts, module documentation and architecture
```

Interactive scans use synchronous HTTP. Kafka provides the asynchronous worker path when Docker is available. Local inference works without Groq. Docker MongoDB is separate from a native MongoDB instance; the launcher selects port 27018 if 27017 is occupied.

The architecture presents the full layered deployment design, including separate phishing, scam, review, image, audio and video modules. Its caption records implementation boundaries; video/audio/review and production controls must be implemented and validated before claiming deployment completion.

## Evidence and development

- [Complete Team Handoff & Setup Manual](docs/TEAM_HANDOFF_AND_SETUP_GUIDE.md)
- [Setup and troubleshooting](docs/TEAM_SETUP.md)
- [Developer workflow](docs/DEVELOPMENT.md)
- [Repository structure and script ownership](docs/REPOSITORY_STRUCTURE.md)
- [Phishing model and measured limitations](docs/phishing/model_card.md)
- [Message/URL integration contract](docs/message-url-fusion.md)
- [Email extension installation](extensions/trustnet-mail/README.md)

Large model weights, secrets, databases, user uploads, environments, training datasets and substantial QA outputs are excluded from Git. Historical experiment dumps were archived outside the application; selected aggregate evaluation reports remain in `models/phishing_url/research/`. Runtime inference has no dependency on an external research folder.
