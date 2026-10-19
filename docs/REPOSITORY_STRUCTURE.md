# Repository structure

The supported local workflow is Windows PowerShell with Python 3.11 and Node.js 24 LTS. Run setup once, then use the three root entry points:

```powershell
.\setup.bat
.\start-dev.bat
.\stop-dev.bat
```

See [team setup](TEAM_SETUP.md) for model packages, prerequisites and environment configuration.

| Location | Responsibility |
| --- | --- |
| `frontend/` | React UI, API adapters, history and PDF export |
| `extensions/trustnet-mail/` | Selected-email extraction and authenticated scan submission |
| `gateway/` | Public API routing, authentication boundary and request handling |
| `services/` | Auth, scan management, image, scam, phishing and trust services |
| `models/` | Inference, preprocessing, explanation and model-specific training utilities |
| `shared/` | Contracts, schemas, authentication helpers, events and shared infrastructure |
| `tests/` | Cross-service contract scenarios |
| `benchmark/` | Image evaluation tools; external labelled data required |
| `scripts/setup/` | Dependency and model installers |
| `scripts/ops/` | Launcher internals, process ownership, Kafka and infrastructure |
| `scripts/checks/` | Integrity, readiness and integration checks |
| `scripts/packaging/` | Model bundles and portable runtime exports |
| `scripts/research/` | Research, data collection, training and historical experiments |
| `docs/` | Setup, developer workflow, contracts, research and architecture |
| `docs/presentation/` | Presentation and viva preparation material |

## Local state and distribution

`.env`, `.venv`, `.venv-scam`, `.venv-phishing`, `runtime_state/`, `runtime-logs/`, `storage_uploads/`, `exports/`, caches and databases are private local state, excluded from Git. `tmp/` is ignored. Existing `auth_dev.db` and `scan_dev.db` remain in place to preserve accounts/history and database URLs. They are not repository deliverables and must not be manually deleted to make a workstation folder look tidy.

Weights are distributed through the checksummed packages described in the setup guide. Existing selected model paths, tokenizer/configuration and the Hugging Face image flow are unchanged. Runtime does not import files from an external research directory. Research commands may require separately retained datasets, historical checkpoints or additional training dependencies; startup does not invoke them.

The application keeps source, model-specific utilities and selected aggregate evidence. Large raw datasets, substantial QA output and archived scratch probes belong outside the application. Unused audio, video, review and OSINT placeholder directories were archived outside the repository. Their design remains documented in the architecture and roadmap; an empty package is not an implemented detector.

## Checks

Quick running-service check:

```powershell
.\.venv-scam\Scripts\python.exe scripts/checks/smoke-message-url.py
```

Auth, plain text/HTML email, actual message and URL inference, persistence and owner isolation:

```powershell
.\.venv\Scripts\python.exe scripts/checks/verify-integration.py
```

Add `--kafka` to that command to verify standalone URL completion through the deployed Kafka worker. The normal mode checks the HTTP fallback. Each run uses isolated application state. Live Gmail installation and model accuracy require their own verification.
