# Developer workflow

[TEAM_SETUP.md](TEAM_SETUP.md) is the single source for installation and startup commands.

## Service boundaries

The browser and Gmail extension call the authenticated Gateway. Scan Management owns relational scan/history records. Scam inference calls the internal phishing `/infer` endpoint for bounded offline link assessment. That endpoint is bound to loopback locally and internal infrastructure in Docker; it is not a public browser API.

Scam/URL workers use separate environments because their selected serialized models require different scikit-learn versions. Do not upgrade the working image `.venv` to satisfy phishing dependencies. The selected phishing runtime does not require BERT, GPU training or the historical external datasets.

Interactive message scans use HTTP. Standalone URL scans use Kafka when enabled, otherwise the same local phishing runtime via HTTP. Worker completions are persisted before acknowledgement/publication according to the worker contract. The synchronous path persists before returning a scan result. No latency or throughput certification follows from a single smoke check.

## Verification

```powershell
.\.venv-scam\Scripts\python.exe -m pytest services/scam_message/tests -q
.\.venv-scam\Scripts\python.exe scripts/checks/smoke-message-url.py
cd frontend
npm run build
cd ..
```

Phishing tests can use `.venv-phishing` plus `services/phishing_url/tests/requirements.txt`. Historical BERT checkpoint/training tests require the separate research dependencies; they are not selected-runtime requirements.

Raw datasets, long experiment histories and substantial QA outputs belong outside the application. Keep selected aggregate evidence, training commands, contracts, licensing records and model installers in Git. Do not remove a runtime import or dependency merely because its filename appears unfamiliar.

Operational scripts are grouped under `scripts/setup`, `scripts/ops`, `scripts/checks` and `scripts/packaging`. Training and data experiments live in `scripts/research`; they are not part of application startup. See [repository structure](REPOSITORY_STRUCTURE.md) for ownership and preservation rules.

The main pytest configuration selects the app and image suites. Scam and phishing suites run separately in their matching environments:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv-scam\Scripts\python.exe -m pytest services/scam_message/tests -q
.\.venv-phishing\Scripts\python.exe -m pytest models/phishing_url/tests services/phishing_url/tests --ignore=models/phishing_url/tests/test_checkpoint.py -q
.\.venv\Scripts\python.exe scripts/checks/verify-integration.py
.\.venv\Scripts\python.exe scripts/checks/verify-integration.py --kafka
```

The historical checkpoint test requires Torch and runs in the main environment. Pytest creates temporary SQLite and upload state before importing settings, so it does not use the workstation's application databases. The platform check uses isolated local services and state in ignored `runtime_state/qa`; model services must already be ready. Its Kafka mode additionally requires the worker infrastructure. Neither check is an accuracy benchmark or a live Gmail test.

The architecture figure distinguishes verified/runtime paths from target modules and deployment extensions. Repository stubs, dependency declarations and infrastructure YAML do not by themselves prove a deployed feature.
