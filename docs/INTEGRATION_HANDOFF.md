# Phishing and message integration handoff

## Latest: explicit saved-link inspection

Message results on the website and Gmail adapter now offer **Inspect this URL**. The protected collector returns separate timestamped domain/IP/TLS/static-HTML evidence, model assessment and unavailable checks. Source message/URL risk remains unchanged. Owner-scoped snapshots persist in history and exported PDFs. See `message-url-fusion.md` for the contract and repeatable checks.

Verified after this addition: main application/image regression suite **171 passed**; dedicated shared evidence checks **3 passed** after malformed-metadata hardening; inspection API delegation/capacity checks **2 passed**; collector/security regression subset **23 passed**; extension worker checks **4 passed**; real authenticated inspection/history/ownership integration passed; synthetic Gmail extraction and actual worker/API/collector flow passed; frontend production build and lint passed. Real website submission, inspection rendering and PDF download were checked. The three-page PDF's evidence text and rendered page layout were reviewed.

The user declined the final live Gmail test. Actual live Gmail extraction, Edge installation and arbitrary-browser support remain unverified. This is not a claim that the extension works in every browser. The existing image models, environments and dependency versions were preserved. No new training or model promotion was performed. A benign appointment/receipt fixture received a high text warning during UI testing, reinforcing the documented false-positive/generalization limitation; it was not relabelled or hidden.

Integration date: 18 October 2026. The `nirmala` branch was fetched and merged into the current working tree with no conflicts. The merge is intentionally **uncommitted** for owner review; nothing was pushed.

## Changes ready for review

- Selected `regional-recall-v1` phishing package installed and checked against the pinned manifest and all eight artifact hashes; a separate `.venv-phishing` avoids dependency changes to image/scam runtimes.
- Website and selected-email extension share message/URL late fusion. Text probabilities and confidence remain separate; the combined maximum-risk warning index is uncalibrated. URL failures, limits and missing checks remain explicit.
- Message reports/history/PDF retain branch scores and embedded-link reasons. The extension no longer describes a low score as “Verified Safe”.
- Local synchronous URL fallback works without Docker. Docker enables Kafka, durable Mongo worker results and an isolated optional live collector for standalone URL scans.
- Public registration always creates a normal user; scan ownership derives from verified JWT identity. Claimed identity/role headers and old demo-ID prefixes do not bypass owner isolation.
- PowerShell startup delegates to the canonical BAT launcher. Stop uses recorded process identity and preserves unrelated processes/volumes. Mongo host-port selection preserves an existing native Mongo instance and its Docker mapping across launches.
- Canonical setup is `docs/TEAM_SETUP.md`. Dated experiment dumps/screenshots and the temporary tracking log were moved to a recoverable external research archive (68 files). Selected aggregate evaluations and useful training scripts remain in Git.

## Verification completed

| Check | Observed result |
| --- | --- |
| Phishing model/service tests | 112 passed in the isolated phishing environment |
| Historical checkpoint utility test | 1 passed in the existing Torch environment |
| Message/URL policy tests | 6 passed, including unavailable service, corrupt response, link cap and score preservation |
| Auth/ownership tests | 11 passed using an isolated QA database |
| Real authenticated API flow | Combined inference, saved report/history, owner isolation, public role restriction and forged identity rejection passed |
| Kafka/Mongo flow | Real queued scan completed through the Docker worker and persisted in Mongo and isolated relational history |
| Collector | DNS, TLS, navigation, HTTP, HTML, registration and reputation observations returned for a public test URL; an observation does not establish safety |
| Browser | Real login, saved combined-result display, new message+URL form submission and actual PDF download checked using Playwright |
| Email extension | DOM/navigation fixtures plus synthetic selected-email DOM → actual worker → authenticated local API passed; Chrome runtime/storage were fixtures |
| Frontend | TypeScript/Vite production build and lint passed |
| Fresh source/artifact export | Real exported scam and phishing API inference passed with declared dependency environments; no external research/dataset folder or exported secrets |
| Image regression | Original `.venv`, cached dima806 ViT and full local detector returned SUCCESS on the retained generated fixture; no network, dependency changes or new accuracy claim |
| Full launcher | `start-dev.bat` reached service readiness and real message/URL smoke success |

Image code, model mapping and dependency specifications were not modified. The generated image fixture retained risk 86.02 with the local Hugging Face analyzer applied; this is a consistency check, not a labelled performance benchmark.

## Evidence boundaries

The message model retains its prior 562/577 held-out result (97.40% accuracy, macro-F1 approximately 0.965), with weaker independent-source generalisation still disclosed. The selected phishing release's imported 313-row convenience-test result is 90.73% accuracy, 92.91% precision, 87.33% recall and 90.03% F1; training/evaluation was not repeated to manufacture an improvement. See `docs/phishing/model_card.md` for source-label and coverage limitations.

The frozen source comparison in `docs/message-url-fusion.md` measures the combined policy on a limited previously inspected collection. Recall increased, false positives increased and F1 decreased; this does not establish production accuracy or calibrate the warning score. Message-only accuracy/precision/recall/F1: **85.32% / 72.81% / 87.37% / 0.7943**. Conservative fusion: **75.77% / 58.00% / 91.58% / 0.7102**. Four extra phishing alerts cost 32 extra false alerts. Seven of the original 300 records were rejected by the input guard; 293 were assessed. Thresholds were not tuned on this test. Aggregate evidence is retained under `models/scam_message/evaluation`.

There is no new image accuracy measurement or claim of live Gmail testing. The revised architecture shows the full deployment design with all six modalities explicitly named; its caption records that audio/video/review and production controls still need implementation and validation. Solid borders describe the design, not a claim of verified deployment completion.

## Running and distribution

On this workstation: ` .\start-dev.bat `, website `http://localhost:5173`, smoke ` .\.venv-scam\Scripts\python.exe scripts/checks/smoke-message-url.py `, stop ` .\stop-dev.bat `.

After the owner reviews, commits and pushes, teammates receive runtime source, frontend/extension, configs, tests, installers, docs and editable architecture via Git. They still need the separate scam and phishing model packages, their own `.env`, image model initial download/cache setup, dependency installation and one-time extension installation/reload. Groq is optional. Model ZIPs and their checksum files are in ignored `exports/`; they are not included in Git. No Git LFS dependency was introduced.

Architecture deliverables are in `docs/architecture/`: editable PPTX, vector PDF and PNG. Full QA logs/databases, old guides and archived experiment output remain outside the application and are not required at runtime.

## Repository organization and verification after cleanup

Root operational entry points remain `setup.bat`, `start-dev.bat` and `stop-dev.bat`. Internal scripts now live in `scripts/setup`, `scripts/ops`, `scripts/checks`, `scripts/packaging` and `scripts/research`. Setup documentation is `docs/TEAM_SETUP.md`; the current developer guide replaces the historical duplicate at `docs/DEVELOPMENT.md`. Presentation material is under `docs/presentation`. See `docs/REPOSITORY_STRUCTURE.md` for ownership.

Scratch probes, empty module scaffolding and the old image developer guide were archived recoverably outside the application. Accounts/history databases remain in their original locations and are ignored, as are `tmp/`, runtime state, secrets, environments and weights. No image model, preprocessing, label mapping, dependency version or checkpoint was replaced. No commit, push or index reset was performed.

The queued URL unit test now explicitly selects its mocked queued path. Separate deterministic tests verify inline URL persistence and an explicit service failure. Pytest uses temporary storage before settings import, rather than application databases. A Windows PowerShell 5.1 JSON-array handling bug in launcher process records was found during restart verification and fixed in the stop and web-service helpers.

Observed verification for this cleanup:

| Check | Result |
| --- | --- |
| Main application/image suite | 162 passed, including the two new inline URL cases |
| Phishing model and service suite | 112 passed in `.venv-phishing`, historical Torch checkpoint test excluded |
| Scam fusion policy suite | 6 passed |
| Frontend | Build and lint passed |
| Phishing report contract | Passed with the moved check script |
| Model integrity | Selected scam verification and all eight phishing component checksums passed |
| Real HTTP fallback integration | Authentication, plain text/HTML message and URL fusion, standalone URL inference, persisted history, owner isolation and public role restriction passed |
| Real Kafka integration | Same authenticated message checks plus standalone URL completion through the deployed worker and saved history passed |
| Launcher | New script paths completed stop, full startup, model readiness and real fusion smoke |
| Clean working-source export | Both selected models loaded and performed real inference without `.env`, user databases or the external research tree; existing declared dependency environments were reused |
| Script validation | PowerShell parsing and Python script parsing passed |

The repeatable integration check is `.\.venv\Scripts\python.exe scripts/checks/verify-integration.py`, with `--kafka` for the deployed worker path. These are functional checks, not new accuracy, live Gmail or fresh dependency-installation results. Prior measured model metrics and combined-score calibration limitations remain unchanged. All pre-existing staged merge work remains available for owner review, along with the new moved files.
