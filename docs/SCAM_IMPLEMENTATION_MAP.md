# Scam implementation map

All paths below are relative to this repository. `../scam/` contains research and QA records only; none is imported by the running application.

| Responsibility | Actual implementation | Caller | Verification |
|---|---|---|---|
| Bounded SMS/email and HTML-to-text input | `shared/schemas/message_input.py` | Scanner route, scam worker, frontend/extension request contract | HTML/script removal, Unicode/subject offsets, oversize/unknown-field contract tests |
| Script/empty/NUL validation | `models/scam_message/preprocessing/validation.py` | Semantic predictor | Hindi/Hinglish/empty and long-input checks |
| Safe URL structure | `models/scam_message/preprocessing/links.py` | Selected hybrid inference and offline lexical training | Finite structural features, malformed URLs, train-fitted scaling; no network requests |
| Calibration/class mapping | `models/scam_message/configs/runtime.py`, `artifacts/{runtime,hybrid_config,manifest}.json` | Detector initialization | Manifest checksums, architecture/label/feature shape checks, tamper rejection |
| Actual local model inference | `models/scam_message/inference/semantic_detector.py` | `models/scam_message/detector.py`; compatibility re-export `semantic_detector.py` | Offline verification, selected artifact identity, cached final predictions versus runtime |
| Predictor-based signed explanation | `models/scam_message/explainability/occlusion.py` | Semantic predictor | Original minus masked probability recomputed against the deployed predictor; bounded partial attribution |
| Separate risk/category/sender/authorship | `models/scam_message/presentation.py` | Scam service and Kafka worker | Low signal never establishes sender identity; sender `NOT_VERIFIED`, authorship `NOT_ASSESSED`; short/unsupported inputs handled |
| Metrics/coverage/confidence intervals | `models/scam_message/evaluation/metrics.py` | External final and ablation evaluation scripts | Three-class confusion matrices, alert versus argmax recall, Wilson intervals, abstentions kept in operational denominator |
| Service/readiness/concurrency | `services/scam_message/app/{main,worker}.py`, `app/config/settings.py` | Gateway/scanner or Kafka request consumer | Actual synchronous API inference, readiness, Kafka acknowledgement/completion/replay/DLQ checks |
| Persistence/history | `services/scan_management/app/{routers/scan_router,services/scan_service,repositories/scan_repository,db_models/scan,completion_consumer}.py` | Gateway/scam route/completion consumer | Original canonical input and complete result survive GET, browser refresh and process restart; failures remain failed |
| Optional provider | `services/scam_message/app/optional_explanation.py` | Explicit website opt-in | Disabled/no-key local behavior; injected mock transport tests timeout, 429, schema/unknown-ID rejection; classification never changes |
| Input and scan flow | `frontend/src/views/scam_message/ScamMessageScanView.tsx`, `services/api/scan.api.ts` | App scanner navigation | Real browser scan and authenticated gateway request |
| Reusable forensic result | `frontend/src/components/scam_message/ScamResult.tsx` | Scan view and `views/ReportView.tsx` | Build/lint, original Unicode text, signed highlights, available/unavailable layers, saved report |
| Browser connection | `frontend/src/services/api/client.ts`, `frontend/vite.config.ts` | Frontend API calls | Same-origin development proxy; actual browser sign-in/session restore/history; production uses fixed local gateway |
| PDF | `frontend/src/services/pdfExporter.ts` | Reusable result's export action | Real browser download parsed against exact saved verdict/risk/model; standard-font Unicode escapes are reversible |
| Gmail integration | `extensions/trustnet-mail/` | Gmail content script, MV3 worker, options | DOM/navigation/stale-response fixtures and actual authenticated worker/API flow; live Gmail status recorded separately |
| Portable installation and service launch | `install-scam-model.py`, `install-scam.ps1`, `start-scam.ps1`, `stop-scam.ps1`, `verify-scam.py`, `scripts/smoke-scam.py` | Teammate commands in `TEAM_SETUP.md` | Independent CPU environment/extracted runtime, integrity and actual inference; owned-process stop; no research folder/cache needed |

Detailed records are under the owner's external `scam/qa/continuation/` (prior baseline integration checks) and `scam/qa/paper-stage/` (current browser, image diagnosis and selected-model checks). Research scripts/checkpoints/predictions are under external `scam/experiments/`; portable checks execute the exported runtime with no imports from those directories. See the final handoff for the precise verification status and blockers; historical fixture checks do not imply live Gmail installation or successful Hugging Face image inference.
