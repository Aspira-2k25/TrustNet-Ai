TrustNet AI — Master Technical Specification 

TRUSTNET AI 

Master Technical Specification 

Architecture · Implementation Blueprint · Research Plan 

Document Conventions 

This specification reconciles the original TrustNet AI Engineering Blueprint with the subsequent Architecture Audit. 
The Blueprint is the primary source of scope, modules, and technology choices; the Audit is the correction and 
hardening layer. Where the two agreed, content is preserved unchanged. Where the Audit identified a gap or 
contradiction, the correction is integrated directly into the relevant section rather than appended separately. Every 
substantive statement in this document carries one of the following status tags: 

• CONFIRMED — stated explicitly in the Blueprint and/or Audit; not invented. 

• AUDIT FIX — a correction or addition the Audit explicitly required, now integrated into the architecture. 

• PROPOSED — a reasonable engineering default filled in because the source documents required a decision to be 
deterministic, but did not specify one. Flagged for team review. 

• TO VERIFY — a detail the team must confirm (dataset access, licensing, external API availability) before 
implementation. 

• FUTURE — explicitly out of MVP scope; documented for completeness, not required for the panel deliverable. 

 

No dataset, model name, metric, API field, or performance number appears in this document unless it was present in 
one of the two source documents or is explicitly tagged PROPOSED/TO VERIFY. No results are reported as 
measured; all evaluation numbers are placeholders until real experiments run. 

  

Page 1 of 63 



TrustNet AI — Master Technical Specification 

Table of Contents 
Document Conventions .................................................................................................................................................... 1 

Table of Contents .............................................................................................................................................................. 2 

1. Project Overview .......................................................................................................................................................... 6 

1.1 What We Are Building ........................................................................................................................................... 6 

1.2 Why We Are Building It ........................................................................................................................................ 6 

1.3 Problems Solved ...................................................................................................................................................... 6 

1.4 System Modules ...................................................................................................................................................... 6 

2. Complete System Architecture .................................................................................................................................... 8 

2.1 High-Level Flow ...................................................................................................................................................... 8 

2.1.1 Why each arrow exists ..................................................................................................................................... 9 

2.1.2 Side paths .......................................................................................................................................................... 9 

3. Universal Risk Score Convention .............................................................................................................................. 10 

3.1 Definition ............................................................................................................................................................... 10 

3.2 Conversion Examples ........................................................................................................................................... 10 

3.3 Where the conversion happens ............................................................................................................................ 10 

4. Standard DetectionResult Contract .......................................................................................................................... 11 

4.1 Field-level notes ..................................................................................................................................................... 12 

4.2 EvidenceItem shape .............................................................................................................................................. 12 

4.3 Full example message — detector.phishing.completed ..................................................................................... 12 

5. Trust Score Engine — Fusion Architecture ............................................................................................................. 13 

5.1 Why fusion is required ......................................................................................................................................... 13 

5.2 Fusion steps ........................................................................................................................................................... 13 

Step 1 — Normalization ......................................................................................................................................... 13 

Step 2 — Weighted combination ........................................................................................................................... 13 

Step 3 — Contradiction detection ......................................................................................................................... 13 

Step 4 — Risk-level mapping ................................................................................................................................. 13 

5.3 Contradiction and confidence handling — worked example ............................................................................ 14 

5.4 Detector availability matrix ................................................................................................................................. 14 

5.5 Evidence aggregation............................................................................................................................................ 15 

6. Failure Handling & Degradation .............................................................................................................................. 16 

6.1 Explicit detector states ......................................................................................................................................... 16 

6.2 Retry policy ........................................................................................................................................................... 16 

6.3 Timeout policy ....................................................................................................................................................... 16 

6.4 Dead-letter queue behavior .................................................................................................................................. 16 

6.5 Idempotency .......................................................................................................................................................... 17 

6.6 Error propagation and user-visible status .......................................................................................................... 17 

6.7 Logging .................................................................................................................................................................. 17 

7. Message Broker Architecture .................................................................................................................................... 18 

7.1 Why an async broker, and when not to use it .................................................................................................... 18 

Page 2 of 63 



TrustNet AI — Master Technical Specification 

7.2 Topic / exchange list.............................................................................................................................................. 18 

7.3 Message schema, correlation, and ordering ....................................................................................................... 18 

7.4 RabbitMQ vs. Kafka — scope note ..................................................................................................................... 19 

8. Database Design .......................................................................................................................................................... 20 

8.1 PostgreSQL — relational core ............................................................................................................................. 20 

8.2 MongoDB — flexible, high-volume documents .................................................................................................. 20 

8.3 Redis — ephemeral, hot-path data ...................................................................................................................... 20 

8.4 What must never be stored in any of these ......................................................................................................... 20 

9. Object Storage ............................................................................................................................................................. 21 

9.1 What goes into object storage vs. metadata storage .......................................................................................... 21 

9.2 Retention................................................................................................................................................................ 21 

10. Authentication & Authorization.............................................................................................................................. 22 

10.1 Token design ....................................................................................................................................................... 22 

10.2 Roles (RBAC) ...................................................................................................................................................... 22 

10.3 Request flow ........................................................................................................................................................ 22 

10.4 The one strict rule ............................................................................................................................................... 22 

10.5 Audit logging ....................................................................................................................................................... 22 

11. API Specification ...................................................................................................................................................... 23 

11.1 Versioning ............................................................................................................................................................ 23 

11.2 Authentication endpoints ................................................................................................................................... 23 

11.3 Scan / upload / URL submission ........................................................................................................................ 23 

11.4 Dashboard / analytics ......................................................................................................................................... 24 

11.5 Admin endpoints ................................................................................................................................................. 24 

11.6 Standard error envelope .................................................................................................................................... 24 

12. Frontend Specification ............................................................................................................................................. 25 

12.1 Pages .................................................................................................................................................................... 25 

12.2 Components ......................................................................................................................................................... 25 

12.3 State management & API integration ............................................................................................................... 25 

12.4 Required UI states .............................................................................................................................................. 25 

12.5 Honesty constraint .............................................................................................................................................. 26 

13. SSRF Protection ........................................................................................................................................................ 27 

13.1 Where this lives in the architecture ................................................................................................................... 27 

13.2 Controls ............................................................................................................................................................... 27 

13.3 Where validation happens ................................................................................................................................. 27 

14. Secure File Upload Pipeline ..................................................................................................................................... 28 

14.1 Pipeline stages, in order ..................................................................................................................................... 28 

14.2 Where validation happens ................................................................................................................................. 28 

15. Privacy & Data Retention ........................................................................................................................................ 29 

15.1 What is stored, and why ..................................................................................................................................... 29 

15.2 Retention.............................................................................................................................................................. 29 

Page 3 of 63 



TrustNet AI — Master Technical Specification 

15.3 Sensitive data handling....................................................................................................................................... 29 

15.4 Access control & logging .................................................................................................................................... 29 

16. AI / ML Detection Modules ..................................................................................................................................... 30 

16.1 Phishing / Malicious URL Detection ................................................................................................................. 30 

16.2 Scam / Fraudulent Message Detection .............................................................................................................. 31 

16.3 Fake Review Detection ....................................................................................................................................... 31 

16.4 Deepfake Detection — Image............................................................................................................................. 32 

16.5 Deepfake Detection — Audio ............................................................................................................................. 33 

16.6 Deepfake Detection — Video ............................................................................................................................. 33 

16.6.1 rPPG constraint — AUDIT FIX ................................................................................................................. 34 

16.7 OSINT Verification Service ............................................................................................................................... 35 

17. Data Leakage Prevention ......................................................................................................................................... 36 

17.1 Leakage risk by modality ................................................................................................................................... 36 

17.2 Split definition ..................................................................................................................................................... 36 

17.3 Reproducible, recorded splits ............................................................................................................................ 36 

17.4 Enforcement ........................................................................................................................................................ 36 

18. Reproducibility ......................................................................................................................................................... 38 

19. Research Evaluation Methodology .......................................................................................................................... 39 

19.1 Evaluation tiers ................................................................................................................................................... 39 

19.2 Metric selection per modality ............................................................................................................................ 39 

19.3 Reporting discipline ............................................................................................................................................ 39 

20. Ablation Study .......................................................................................................................................................... 40 

21. Research Contribution ............................................................................................................................................. 41 

21.1 What is proposed as a contribution................................................................................................................... 41 

21.2 Distinguishing existing work from this project's contribution ....................................................................... 41 

21.3 Overclaiming discipline ...................................................................................................................................... 41 

22. Repository & Folder Structure ................................................................................................................................ 42 

22.1 Full repository tree ............................................................................................................................................. 42 

22.2 Model folder skeleton (identical across all seven modalities) ......................................................................... 42 

22.3 CI/CD workflows ................................................................................................................................................ 43 

23. Configuration Management ..................................................................................................................................... 44 

23.1 What must never be committed to Git .............................................................................................................. 44 

24. Observability ............................................................................................................................................................. 45 

25. Testing Strategy ........................................................................................................................................................ 46 

26. Security Test Plan ..................................................................................................................................................... 47 

27. Deployment Architecture ......................................................................................................................................... 48 

27.1 Docker .................................................................................................................................................................. 48 

27.2 Docker Compose vs. Kubernetes — honest guidance ...................................................................................... 48 

27.3 Actual student deployment target ..................................................................................................................... 48 

28. Development Roadmap ............................................................................................................................................ 49 

Page 4 of 63 



TrustNet AI — Master Technical Specification 

29. MVP / Research Enhancement / Future Classification ......................................................................................... 53 

30. Risk Register ............................................................................................................................................................. 54 

31. Architecture Decision Records (ADRs) .................................................................................................................. 56 

ADR 0001: Message broker choice — Kafka vs. RabbitMQ .............................................................................. 56 

ADR 0002: Docker Compose vs. Kubernetes ....................................................................................................... 56 

ADR 0003: Modular monolith vs. full microservices........................................................................................... 56 

ADR 0004: Universal risk_score direction convention ........................................................................................ 56 

ADR 0005: Deterministic weighted-average fusion for v1 (no learned meta-model) ....................................... 57 

32. Requirements Traceability Matrix .......................................................................................................................... 58 

33. Implementation Acceptance Checklist .................................................................................................................... 60 

Architecture ............................................................................................................................................................ 60 

Security .................................................................................................................................................................... 60 

Authentication ......................................................................................................................................................... 60 

Database .................................................................................................................................................................. 60 

Storage ..................................................................................................................................................................... 60 

Datasets .................................................................................................................................................................... 60 

Preprocessing .......................................................................................................................................................... 60 

Models ...................................................................................................................................................................... 60 

Training ................................................................................................................................................................... 60 

Evaluation ................................................................................................................................................................ 60 

Inference .................................................................................................................................................................. 61 

Schemas ................................................................................................................................................................... 61 

Broker ...................................................................................................................................................................... 61 

Fusion ....................................................................................................................................................................... 61 

Contradiction detection .......................................................................................................................................... 61 

Explainability .......................................................................................................................................................... 61 

Frontend .................................................................................................................................................................. 61 

Testing...................................................................................................................................................................... 61 

Observability ........................................................................................................................................................... 61 

Deployment .............................................................................................................................................................. 61 

Documentation ........................................................................................................................................................ 61 

Research experiments ............................................................................................................................................. 61 

Appendix A — Glossary ................................................................................................................................................. 63 

 
  

Page 5 of 63 



TrustNet AI — Master Technical Specification 

1. Project Overview 

1.1 What We Are Building 

TrustNet AI is a microservices-based digital-trust platform that ingests user-submitted content — URLs, text messages, 
product/business reviews, images, audio clips, and videos — and returns a single, explainable Trust Score indicating 
how likely that content is to be malicious, fabricated, or deceptive. The score is produced by fusing the outputs of 
independent, per-modality AI detectors (phishing/URL, scam message, fake review, image deepfake, audio deepfake, 
video deepfake, and OSINT verification) through a deterministic Trust Score Engine. 

1.2 Why We Are Building It 

Phishing links, AI-voice scam calls, fabricated reviews, and deepfake media are increasingly used together in 
coordinated deception campaigns, but existing tools evaluate each threat type in isolation. TrustNet AI's contribution is 
not any single detector — each modality already has published, precedented approaches — but the fusion layer: a 
confidence-aware, risk-normalized, explainable combination of multiple independent detectors, with contradiction-
aware handling of disagreement between them (Section 21, Research Contribution, states this claim precisely and non-
speculatively). 

1.3 Problems Solved 

• A single URL, message, or media file can be screened against multiple threat categories in one request instead of 
five separate tools. 

• Users receive one interpretable risk number (0-100) and a plain-language explanation, not seven disconnected 
model outputs. 

• Partial system failure (one detector down or slow) degrades gracefully instead of blocking the whole scan — 
Section 6. 

• Detector disagreement is surfaced explicitly rather than silently averaged away — Section 5.3. 

1.4 System Modules 

Module Type Responsibility 

Frontend (React 19 + TS) Client Upload center, dashboard, scan status, results, reports, auth UI 

API Gateway Sync Routing, auth check, rate limiting, request validation 

Authentication Service REST Login/register, JWT issuance, refresh, RBAC 

Scan Management Service REST Create scan, track lifecycle, orchestrate fan-out 

AI Orchestration Service Hybrid Routes scan content to correct detector(s), tracks completion 

Kafka 
Phishing Detection Service URL/domain feature extraction + LightGBM+BERT inference 

consumer 

Scam Message Detection Kafka 
Text classification (DistilBERT) 

Service consumer 

Fake Review Detection Kafka 
Review text + behavioral analysis (SBERT/XGBoost) 

Service consumer 

Kafka 
Image Deepfake Service Face-forensic image classification (EfficientNet-B0) 

consumer 

Kafka 
Audio Deepfake Service MFCC + BiLSTM synthetic-speech detection 

consumer 

Kafka 
Video Deepfake Service Frame-level reuse of image model + temporal aggregation 

consumer 

Page 6 of 63 



TrustNet AI — Master Technical Specification 

Module Type Responsibility 

Kafka 
OSINT Service External verification / metadata cross-check 

consumer 

Trust Score Engine Hybrid Normalization, weighted fusion, contradiction detection, risk mapping 

Explainability Service Hybrid Aggregates per-module evidence into a human-readable report 

Notification Service Hybrid Email / in-app alerts 

Analytics Service REST Aggregated dashboard statistics 

Report Generation Service REST PDF/HTML report assembly 

REST, admin-
Dataset Service Training-data versioning and manifests 

only 
Table 1.1 — CONFIRMED. Reproduced from Blueprint Part C Service Directory; module boundaries unchanged by the Audit. 

Page 7 of 63 



TrustNet AI — Master Technical Specification 

2. Complete System Architecture 

2.1 High-Level Flow 

 
Figure 2.1 — CONFIRMED, reproduced from Blueprint Part A/H and expanded to name every arrow, per Audit item 15. 

 

 

Page 8 of 63 



TrustNet AI — Master Technical Specification 

2.1.1 Why each arrow exists 

• User -> Frontend -> Gateway: single TLS-terminated entry point; the Gateway is the only component the public 
internet reaches directly. 

• Gateway -> Auth: every request's JWT is verified locally against Auth's signing key before any business logic 
runs (no per-request network round-trip to Auth). 

• Scan Mgmt -> Object Storage: raw media never touches a database row; only a storage key/URL is persisted 
(Section 9). 

• Scan Mgmt -> Broker -> Detectors: async fan-out so the user is not blocked on slow AI inference; the Gateway 
returns 202 immediately (Blueprint Part H, step 8). 

• Detectors -> Trust Score Engine: consumed via the wildcard detector.*.completed subscription; fusion only 
proceeds once all expected detectors have reported or a timeout fires (Section 5). 

• Trust Score Engine -> Explainability -> Persistence -> Frontend: the fused, explainable result is written once and 
read many times by polling clients. 

2.1.2 Side paths 

• Errors: any layer raises a typed exception; a shared error-handling middleware converts it to the standard {data, 
error, meta} envelope (Blueprint Part O). 

• Retries / DLQ: consumer-side retry with exponential backoff (3 attempts), then publication to <topic>.dlq; a 
monitoring alert fires on any DLQ arrival (Blueprint Part G, Section 8). 

• Logging: every request/scan carries a request_id / scan_id threaded through every Kafka event and service call 
(Blueprint Part O). 

• Metrics: Prometheus scrapes /metrics on every service; Grafana dashboards for system health, AI-pipeline 
latency, and broker consumer lag (Blueprint Part K). 

• Audit logs: append-only records in MongoDB audit_logs / detection_logs for every scan and every admin action 
(Blueprint Part F). 

• Notifications / status: the frontend polls GET /orchestration/{scan_id}/status; Notification Service additionally 
pushes email/in-app alerts on trust_score.generated. 

Page 9 of 63 



TrustNet AI — Master Technical Specification 

3. Universal Risk Score Convention 

Status:  [AUDIT FIX]  — the Blueprint's per-module scores were not guaranteed to share a common direction. This 
section defines the single convention every detector and every downstream consumer must follow. 

3.1 Definition 

Every detector emits a risk_score, an integer or float in the closed interval [0, 100], with a fixed, non-negotiable 
direction: 

  0   = lowest risk  / content is safe / authentic / legitimate 
100  = highest risk / content is malicious / fabricated / suspicious 

This direction is fixed system-wide. No module, service, or downstream consumer is permitted to reinterpret it. This 
eliminates the single most dangerous class of silent fusion bug: two modules whose native scores point in opposite 
directions being averaged as if they agreed. 

3.2 Conversion Examples 

Detector Native output native_score_semantics risk_score conversion 

probability_of_positive_class risk_score = round(0.90 
Phishing phishing probability = 0.90 

(phishing) * 100) = 90 

risk_score = round(0.90 
Scam Message spam/scam probability = 0.90 probability_of_positive_class (scam) 

* 100) = 90 

risk_score = round(0.90 
Fake Review fake probability = 0.90 probability_of_positive_class (fake) 

* 100) = 90 

authenticity probability = 0.90 (i.e. probability_of_negative_class risk_score = round((1 - 
Image Deepfake 

90% real) (authentic) 0.90) * 100) = 10 

risk_score = round(0.90 
Audio Deepfake spoof probability = 0.90 probability_of_positive_class (spoof) 

* 100) = 90 

fake probability (video-level risk_score = round(0.72 
Video Deepfake probability_of_positive_class (fake) 

aggregate) = 0.72 * 100) = 72 

corroboration_score = 0.20 (low probability_of_negative_class risk_score = round((1 - 
OSINT 

external corroboration) (verified genuine) 0.20) * 100) = 80 
Table 3.1 — AUDIT FIX. Direction examples for phishing/fake/authenticity were given explicitly in the Audit; OSINT and video rows are 
PROPOSED, following the same rule, for team confirmation. 

3.3 Where the conversion happens 

The conversion is not a Trust Score Engine responsibility — it happens inside each detector's own inference/predict.py 
wrapper, immediately after the native model output is produced and before the DetectionResult is published to Kafka. 
This is enforced by the shared DetectionResult schema (Section 4): risk_score is a required field with no corresponding 
'native_score direction' flag downstream, so a module that fails to convert correctly produces an obviously wrong 
number the Trust Score Engine's input-validation step (Section 5.2) will reject at schema-validation time, not silently 
fuse. 

• Each module's models/<modality>/configs/model_config.yaml (Blueprint Part D) declares 
native_score_semantics and the exact conversion formula for that model version — this is part of the model 
configuration artifact, not a hardcoded constant, so retraining with a differently-oriented output only requires a 
config change. 

• shared/schemas/detection_result.py (Blueprint Section 5) defines risk_score as a validated float in [0,100] — a 
value outside this range fails Pydantic validation before the message is ever published. 

Page 10 of 63 



TrustNet AI — Master Technical Specification 

4. Standard DetectionResult Contract 

Status:  [AUDIT FIX]  — expands the Blueprint's {score, confidence, label, evidence, metadata} shape into a 
production-ready contract supporting fusion, debugging, reproducibility, observability, explainability, versioning, and 
partial failure. 

This is the single schema every detector service publishes on its detector.<name>.completed topic, and the only shape 
the Trust Score Engine consumes. It supersedes, and is backward-compatible with, the explainability shape in Blueprint 
Part I (prediction/confidence/evidence/metadata/heatmap_ref map onto 
label/confidence/evidence/metadata/evidence[].heatmap_ref below). 

Field Type Meaning / allowed values Example 

Correlates this result to its parent scan 
scan_id string (UUID) "scan_7a1b2c" 

across every service 

phishing | scam_message | fake_review | 
module enum string image_deepfake | audio_deepfake | "phishing" 

video_deepfake | osint 

Stable identifier of the specific detector 
detector_id string "phishing.lgbm_bert.v1" 

implementation (allows A/B model variants) 

string (semver-
model_version Version of the trained model artifact used "bert_v1+lgbm_v1" 

like) 

Version of the preprocessing pipeline 
preprocessing_version string applied — required for reproducibility "pp_v3" 

(Section 18) 

The model's raw, unconverted output, 
native_score float 0.90 

exactly as produced 

probability_of_positive_class | 
native_score_semantics enum string probability_of_negative_class | "probability_of_positive_class" 

distance_score | anomaly_score 

Universal risk score per Section 3 — 
risk_score float [0,100] 90 

REQUIRED, validated at publish time 

Model's own calibrated confidence in its 
confidence float [0,1] 0.97 

prediction (not the same axis as risk_score) 

Human-readable classification the module 
label string "phishing" 

assigned 

SUCCESS | PARTIAL_SUCCESS | 
status enum string FAILED | TIMEOUT | SKIPPED | "SUCCESS" 

UNAVAILABLE — see Section 6 

{feature_or_region, contribution, 
evidence list[EvidenceItem] human_readable_note} items driving the see Section 4.2 

decision 

Optional natural-language, per-detector 
"Domain registered 9 days 

explanation string | null explanation (input to the Explainability 
ago..." 

Service) 

Raw supporting facts a human reviewer 
metadata dict might want (domain age, frame count, {"domain_age_days": 9} 

sample rate) 

Wall-clock inference time for this detector 
processing_time_ms int 340 

call 

ISO-8601 
timestamp When this result was produced (UTC) "2026-08-08T10:15:06Z" 

datetime 

Populated only when status is 
error_code string | null "MODEL_TIMEOUT" 

FAILED/TIMEOUT/UNAVAILABLE 

Page 11 of 63 



TrustNet AI — Master Technical Specification 

Field Type Meaning / allowed values Example 

Human-readable error detail, populated only "Inference exceeded 5000ms 
error_message string | null 

alongside error_code budget" 

DetectionResult contract version (starts at 1, 
schema_version int per Blueprint Part G event-versioning 1 

convention) 
Table 4.1 — AUDIT FIX. scan_id/module/status/evidence/metadata/label/confidence are CONFIRMED from the Blueprint's explainability 
shape; detector_id, model_version, preprocessing_version, native_score, native_score_semantics, risk_score, explanation, 
processing_time_ms, timestamp, error_code, error_message, schema_version are AUDIT FIX additions. 

4.1 Field-level notes 

• scan_id + module together form the idempotency key used by every consumer (Blueprint Part G reliability 
mechanics), unchanged by this expansion. 

• risk_score and confidence are deliberately separate axes: risk_score says how dangerous the content looks; 
confidence says how much the model trusts its own answer. A detector can report risk_score=90, 
confidence=0.40 (looks dangerous, but the model is unsure) — this combination matters directly to fusion 
(Section 5.2) and to contradiction detection (Section 5.3). 

• error_code / error_message are only populated when status != SUCCESS and status != PARTIAL_SUCCESS; a 
SUCCESS result MUST have both null. 

4.2 EvidenceItem shape 

{ 
  "feature_or_region": "domain_age_days",   // string 
  "contribution": 0.31,                       // float, relative weight of this signal 
  "human_readable_note": "Domain registered 9 days ago" 
} 

Listing 4.1 — CONFIRMED, reproduced from Blueprint Section 7 Kafka event example. 

4.3 Full example message — detector.phishing.completed 

{ 
  "schema_version": 1, 
  "scan_id": "scan_7a1b2c", 
  "module": "phishing", 
  "detector_id": "phishing.lgbm_bert.v1", 
  "model_version": "bert_v1+lgbm_v1", 
  "preprocessing_version": "pp_v3", 
  "native_score": 0.90, 
  "native_score_semantics": "probability_of_positive_class", 
  "risk_score": 90, 
  "confidence": 0.97, 
  "label": "phishing", 
  "status": "SUCCESS", 
  "evidence": [ 
    {"feature_or_region": "domain_age_days", "contribution": 0.31, 
     "human_readable_note": "Domain registered 9 days ago"}, 
    {"feature_or_region": "ssl_present", "contribution": 0.28, 
     "human_readable_note": "No valid SSL certificate"} 
  ], 
  "explanation": "This URL was flagged high-risk phishing: young domain, no SSL.", 
  "metadata": {"domain_age_days": 9, "ssl_present": false}, 
  "processing_time_ms": 340, 
  "timestamp": "2026-08-08T10:15:06Z", 
  "error_code": null, 
  "error_message": null 
} 

Listing 4.2 — AUDIT FIX. Extends the Blueprint's Section 7 sample event with every new required field. 

Page 12 of 63 



TrustNet AI — Master Technical Specification 

5. Trust Score Engine — Fusion Architecture 

Status:  [CONFIRMED + AUDIT FIX]  — the four-step fusion architecture (normalize, weight, contradict, map) is 
preserved unchanged from Blueprint Part I. The Audit's contribution is making detector-availability handling explicit 
and exhaustive (Section 5.4) and formalizing the missing/failed/timeout cases. 

5.1 Why fusion is required 

Each detector reasons over a different modality with a different native scoring convention and a different reliability 
profile. A single number a non-technical user can act on requires combining these into one comparable scale (Section 
3) and one combined judgment. Fusion is what turns seven independent model outputs into one Trust Score. 

5.2 Fusion steps 

Step 1 — Normalization 

Every module's native output is converted to risk_score in [0,100] inside the detector itself (Section 3.3), before the 
Trust Score Engine ever sees it. The Engine's own normalization step is a validation pass: reject/flag any 
DetectionResult whose risk_score is missing, out of range, or whose status is not SUCCESS/PARTIAL_SUCCESS. 

Step 2 — Weighted combination 

A validation-set-derived weight per module (following the BGL-PhishNet precedent of cross-validated weighting cited 
in the Blueprint's literature review) combines the normalized scores. V1 is a deterministic weighted average — 
CONFIRMED, the Blueprint explicitly rejects a learned meta-model until the simple version is working and measured, 
and the Audit does not override this. 

trust_risk_score = sum(risk_score_i * weight_i for i in reporting_modules) 
                   / sum(weight_i for i in reporting_modules) 
  
# weight_i is derived from module i's held-out validation performance 
# (Section 19); weights are re-derived whenever a model is retrained 
# and re-evaluated, never hand-tuned without an evaluation run behind it. 

• Minimum/maximum weight rule [PROPOSED]: no single module's weight may exceed 0.40 of the total, so one 
detector cannot unilaterally dominate the fused score even if its validation accuracy is highest — this needs 
guide/team sign-off before being treated as CONFIRMED policy. 

• Weights live in trust-engine-service/config/fusion_weights.yaml (Blueprint Section 3 service layout) — never 
hardcoded in Python, versioned alongside the model_version that produced them. 

Step 3 — Contradiction detection 

A rule layer checks for sharp disagreement between modules — e.g., the image detector says 'authentic' while OSINT 
reports the same image was previously flagged elsewhere as manipulated. CONFIRMED as the Blueprint's stated most-
novel component; kept simple and rule-based, not a black box, per Blueprint Part I. 

• Trigger condition [PROPOSED, pending team-defined threshold]: two or more reporting modules whose 
risk_scores differ by more than a configured delta (e.g., 40 points) on content that logically should correlate (e.g., 
OSINT vs. image on the same asset). 

• Effect: the fused score is NOT silently averaged away. A contradiction_flag=true is attached to the trust score 
record, a confidence penalty is applied (Section 5.2, Step 4), and the specific disagreeing modules are surfaced in 
the explanation. 

• Build order — CONFIRMED: implement Steps 1-2 first against two real modules (phishing + scam message), 
then add Step 3 only once three or more modules are live (Blueprint Part I build-order note) — there is nothing to 
contradict with fewer than two independent signals on the same content. 

Step 4 — Risk-level mapping 

Page 13 of 63 



TrustNet AI — Master Technical Specification 

The final 0-100 score maps to Low/Medium/High/Critical via fixed, documented thresholds — not learned — so the 
mapping is auditable in a viva. CONFIRMED from Blueprint Part I. 

trust_risk_score range risk_level Notes 

[PROPOSED default thresholds — confirm against literature-
0 – 24 Low 

review precedent before freezing] 

25 – 49 Medium  

50 – 74 High  

75 – 100 Critical  
Table 5.1 — PROPOSED. The Blueprint states thresholds are fixed and documented but does not give exact cut points in the provided 
excerpt; the boundaries above are a reasonable, evenly-spaced default the team must confirm or override before freezing Phase 0 (Section 
28). 

5.3 Contradiction and confidence handling — worked example 

Case Modules reporting Fusion behavior 

Agreement phishing=90, osint=85 (both high) Standard weighted average; no flag. 

image_deepfake=10 (looks authentic), contradiction_flag=true; confidence penalty applied; both 
Contradiction osint=90 (flagged elsewhere as pieces of evidence surfaced side-by-side in the explanation 

manipulated) rather than averaged into a misleadingly moderate score. 

Module's contribution is still included (weighted average uses 
scam_message risk_score=88 but risk_score, not confidence directly), but confidence=0.35 is 

Low confidence 
confidence=0.35 surfaced in the explanation and lowers the overall trust_score 

confidence field so the user is told the result is less certain. 
Table 5.2 — AUDIT FIX. Explicit worked cases were not present in the Blueprint excerpt; the Audit requires them documented. 

5.4 Detector availability matrix 

Status:  [AUDIT FIX]  — every possible availability combination must be enumerated so the fusion engine never 
silently breaks. 

Case Fusion behavior trust_score record 

All modules available Standard weighted average over all reporting modules. partial=false 

Weighted average over the modules relevant to this content type 
Some modules 

only (e.g., a text-only scan never expects an image score) — 
available (scan type partial=false 

CONFIRMED, Blueprint Part I: 'a plaintext scam-message scan 
doesn't trigger all) 

never produces an image score.' 

Excluded from the weighted average; remaining modules' weights 
are NOT renormalized to sum to 1 silently — instead the fused 

One module failed partial=true 
score is computed over available weights and partial=true is set so 
the UI can show 'result based on N of M expected signals.' 

Same as failed; DetectionResult.status=TIMEOUT recorded for 
One module timed out audit; orchestration proceeds after the configured timeout budget partial=true 

rather than blocking indefinitely. 

Fusion proceeds on that single module's risk_score; risk_level 
Only one module partial=true, 

mapping still applies, but the UI must clearly indicate low signal 
returned low_signal_diversity=true 

diversity. 

Fusion does NOT produce a fabricated score. Scan status is set to 
No detector returned FAILED with error_code=NO_DETECTOR_RESPONSE; user no trust_score record created 

sees an explicit failure, not a fake '0' or '50'. 

Section 5.3 — contradiction_flag=true, confidence penalty, partial=false, 
Contradictory results 

evidence surfaced explicitly. contradiction_flag=true 

Page 14 of 63 



TrustNet AI — Master Technical Specification 

Case Fusion behavior trust_score record 

Included in the average, but confidence is propagated into the 
Low-confidence partial=false, confidence 

trust_score's own confidence field (a weighted average of module 
results reduced 

confidences), not silently dropped. 
Table 5.3 — AUDIT FIX. This is the direct implementation of Audit requirement §3 (Trust Score Fusion) and closes the corresponding item 
on the Final Self-Audit checklist. 

5.5 Evidence aggregation 

The Trust Score Engine does not re-derive evidence; it references the evidence[] lists already produced by each 
contributing DetectionResult (Section 4.2) and passes the union of these, plus its own contradiction findings, to the 
Explainability Service. This keeps the Engine's own logic small, testable, and exactly what Blueprint Part R describes 
as 'business logic, not a library problem' — CONFIRMED, no third-party fusion framework is introduced. 

Page 15 of 63 



TrustNet AI — Master Technical Specification 

6. Failure Handling & Degradation 

Status:  [AUDIT FIX]  — the Blueprint already established the principle (Part N risk register: 'a failed deepfake service 
should not prevent the phishing result from still reaching the user') but did not name explicit states. This section makes 
them explicit and binding. 

6.1 Explicit detector states 

State Meaning What happens to the scan 

Detector completed and returned a valid 
SUCCESS Included in fusion at full weight. 

DetectionResult. 

Detector completed but with degraded 
confidence or an incomplete evidence set Included in fusion; confidence penalty applied; 

PARTIAL_SUCCESS 
(e.g., OSINT reached only some external partial=true noted at the module level. 
sources). 

Detector raised an unrecoverable error (bad Excluded from fusion; error_code/error_message 
FAILED input, model load failure) after exhausting recorded; scan proceeds with remaining modules 

retries. (Section 5.4). 

Excluded from fusion once the budget expires; scan 
Detector did not respond within its proceeds; a late-arriving result after timeout is 

TIMEOUT 
configured latency budget. logged but not retroactively fused into an already-

generated trust_score. 

Detector was never invoked because the 
Not counted as a failure anywhere; simply absent 

SKIPPED content type does not apply to it (e.g., image 
from the expected-detector set for this scan. 

detector on a text-only scan). 

Orchestration does not even publish 
Detector service itself is down / unreachable detection.requested to this consumer; scan proceeds 

UNAVAILABLE 
at dispatch time (health check failing). with the remaining available modules, exactly as a 

FAILED case for fusion purposes. 
Table 6.1 — AUDIT FIX. Directly satisfies Audit requirement §4. 

6.2 Retry policy 

• Consumer-side retry with exponential backoff, 3 attempts, for transient failures (a model server briefly 
unavailable) — CONFIRMED, Blueprint Part G reliability mechanics. 

• After retries are exhausted, the message is published to <topic>.dlq instead of being dropped silently, and a 
monitoring alert fires — CONFIRMED, Blueprint Part G. 

6.3 Timeout policy 

• Each detector has a per-modality timeout budget [PROPOSED default: 5000 ms for text/URL detectors, 15000 
ms for image, 20000 ms for audio, 45000 ms for video — the Blueprint does not give exact numbers; these must 
be confirmed against real measured inference latency in Phase 4/12, Section 28]. 

• AI Orchestration Service tracks expected-vs-received detector count per scan in Redis (CONFIRMED, Blueprint 
Part N risk register: 'fusion only triggers once complete, or a timeout fires and fusion proceeds with what's 
available, clearly flagged as partial'). 

6.4 Dead-letter queue behavior 

A poison message (one that fails processing on every retry) is routed to <topic>.dlq rather than reprocessed indefinitely 
or dropped. DLQ arrival is a first-class alert (Blueprint Part K minimum alert set). DLQ messages retain their original 
scan_id/detector_type so an operator can manually replay them once the underlying issue (e.g., a bad model 
deployment) is fixed. 

Page 16 of 63 



TrustNet AI — Master Technical Specification 

6.5 Idempotency 

Every DetectionResult message carries scan_id + module as a stable key; consumers (Trust Score Engine, Scan 
Management) check whether a result for that key has already been processed before writing, so Kafka/RabbitMQ's at-
least-once delivery guarantee never causes double-counting or duplicate notifications — CONFIRMED, Blueprint Part 
G. 

6.6 Error propagation and user-visible status 

The Gateway never returns a raw stack trace. Every error surfaces through the standard envelope {data: null, error: 
{code, message}, meta: {request_id}} (CONFIRMED, Blueprint Part O). For scan status specifically, GET 
/orchestration/{scan_id}/status (Section 11) exposes detectors_expected, detectors_completed, and progress_percent so 
the frontend can show partial progress honestly rather than a binary success/failure. 

6.7 Logging 

Every failure, retry, timeout, and DLQ event is logged as structured JSON carrying the 
request_id/scan_id/detector_type/error_code, so a single failed scan can be traced end-to-end across every service it 
touched — CONFIRMED, Blueprint Part O. 

Page 17 of 63 



TrustNet AI — Master Technical Specification 

7. Message Broker Architecture 

Status:  [CONFIRMED]  — RabbitMQ is the actual MVP broker; Kafka is the documented production target. The Audit 
explicitly requires this distinction be preserved and never accidentally inverted; it is preserved unchanged here (see 
ADR 0001, Section 31). 

7.1 Why an async broker, and when not to use it 

• Use the broker for: scan-creation fan-out to detectors, detector-completion events feeding the Trust Score Engine, 
trust_score.generated events feeding notification/analytics/reporting — anything async, multi-consumer, or 
latency-tolerant. 

• Do NOT use the broker for: login (needs an immediate response — synchronous HTTP to Auth Service), 
fetching scan history for the dashboard (direct synchronous DB read via the Gateway), or any request the user is 
actively waiting on within a second or two. 

CONFIRMED verbatim from Blueprint Part G. 

7.2 Topic / exchange list 

Topic Producer Consumer(s) Purpose 

scan.created Scan Mgmt AI Orchestration New scan needs routing to detectors 

Corresponding detector Per-content-type routing keeps unrelated 
detection.requested.<type> AI Orchestration 

service only detectors idle 

Carries the DetectionResult payload 
detector.<name>.completed Each detector Trust Engine, Scan Mgmt 

(Section 4) 

Notification, Explainability, 
trust_score.generated Trust Engine Fusion complete; downstream fan-out 

Analytics 

Report Service (on demand), 
explanation.generated Explainability Human-readable report content ready 

Analytics 

<topic>.dlq (one per topic Broker, on 
Ops/alerting Poison-message capture (Section 6.4) 

above) exhausted retries 
Table 7.1 — CONFIRMED, reproduced from Blueprint Part G Topic list, with the .dlq row made explicit per Audit item 4/16. 

7.3 Message schema, correlation, and ordering 

• Every event payload carries scan_id and, for detector events, module — the correlation/idempotency key 
described in Section 6.5. 

• Every event carries schema_version (starts at 1) — CONFIRMED, Blueprint Part G event-versioning note: 'costs 
nothing now and is the difference between a clean and a painful schema change later.' 

• Ordering: not guaranteed or required across different detector topics (they are independent, parallel fan-out 
consumers); ordering within a single detector's own topic partition/queue is preserved by the broker and is 
sufficient, since the Trust Score Engine keys its completion tracking by scan_id, not by arrival order. 

• Consumer behavior: each detector service consumes only its own detection.requested.<type> topic, filtered by 
content type — CONFIRMED, Blueprint Part D plugin architecture note: 'a new detector just needs to consume 
detection.requested events filtered by its content type... no other service's code changes.' 

 

 

 

Page 18 of 63 



TrustNet AI — Master Technical Specification 

7.4 RabbitMQ vs. Kafka — scope note 

For the actual student build, RabbitMQ (listed as an alternative in the original project proposal) is the pragmatic MVP 
broker if Kafka's operational overhead (Zookeeper/KRaft, partition management) would eat into the timeline. The 
event-driven pattern is identical either way; only the broker changes. Kafka is presented in the architecture diagram as 
the production target. RabbitMQ is a legitimate, faster-to-operate substitute for the weeks-6-through-16 build. This is 
CONFIRMED verbatim from Blueprint Part G and is the exact distinction Audit item 16 requires be preserved — 
Kafka must never be made mandatory for the student MVP. 

Page 19 of 63 



TrustNet AI — Master Technical Specification 

8. Database Design 

Status:  [CONFIRMED]  — three data stores, each earning its place by access pattern. Ownership model preserved 
unchanged; the Audit did not request an additional database and explicitly rejects introducing one. 

8.1 PostgreSQL — relational core 

Table Key columns Owning service Key indexes 

users id, email, password_hash, role, created_at Auth Service email (unique) 

roles / permissions id, name, permission_flags Auth Service name (unique) 

id, user_id, content_type, status, created_at, user_id, status, 
scans Scan Mgmt 

completed_at created_at 

id, scan_id, overall_score, risk_level, 
trust_scores Trust Engine scan_id (unique) 

confidence, created_at 

reports id, scan_id, report_url, generated_at Report Service scan_id 

notifications id, user_id, scan_id, channel, sent_at, status Notification Service user_id, sent_at 
Table 8.1 — CONFIRMED, Blueprint Part F. Relationships: users 1—N scans; scans 1—1 trust_scores; scans 1—N reports; users 1—N 
notifications. Foreign keys enforced at the DB level. 

8.2 MongoDB — flexible, high-volume documents 

Collection Shape Why Mongo, not Postgres 

One document per detector per scan (Section 4 
detection_results Schema varies per detector 

DetectionResult schema, stored verbatim) 

{scan_id, natural_language_summary, Large, nested, read-heavy, assembled 
explanations 

per_modality_evidence[], heatmap_refs[]} documents 

audit_logs / 
High-volume append-only event records Never needs joins; write-heavy 

detection_logs 

osint_metadata Loosely structured external-verification results No fixed schema across sources 
Table 8.2 — CONFIRMED, Blueprint Part F. Note: detection_results now stores the expanded DetectionResult contract of Section 4 
(AUDIT FIX), not the earlier {score, confidence, label, evidence, metadata} shape — same collection, richer document shape. 

8.3 Redis — ephemeral, hot-path data 

• Session tokens / refresh-token blocklist (short TTL, checked on every authenticated request). 

• Rate-limit counters per user/IP. 

• Frequently-scanned URL cache, with a sensible TTL since domain reputation can change. 

• In-flight scan orchestration state — which of the N expected detectors have reported for scan X (Section 5.4, 6.3). 

CONFIRMED, Blueprint Part F. 

8.4 What must never be stored in any of these 

• Raw uploaded media files — belong in Object Storage (Section 9); databases store only a reference key/URL. 

• Plaintext passwords or raw JWT secrets — hashed passwords only (bcrypt/argon2); secrets belong in 
environment variables / a secret manager. 

• Large model checkpoints or training datasets — belong in object storage or the model registry (Section 18). 

CONFIRMED verbatim, Blueprint Part F. 

Page 20 of 63 



TrustNet AI — Master Technical Specification 

9. Object Storage 

Status:  [CONFIRMED]  — MinIO locally, S3-compatible API in deployment, per Blueprint Part R. 

MinIO (self-hosted, S3-compatible) is used for local/dev; AWS S3 (or MinIO again) for actual deployment — the S3-
API compatibility means code never changes between local dev and cloud deployment. 

9.1 What goes into object storage vs. metadata storage 

Content Storage Notes 

Original uploads (images, audio, Database stores only the object key/URL, never the 
S3/MinIO 

video) binary (Section 8.4). 

Processed media (resized frames, 
S3/MinIO Written by the relevant detector's preprocessing/ step. 

extracted audio segments) 

Generated artifacts (Grad-CAM S3/MinIO, referenced by 
Section 4.2 evidence items may reference these keys. 

heatmaps, waveform highlights) explanations.heatmap_refs[] 

Written by Report Generation Service; reports.report_url 
Generated PDF/HTML reports S3/MinIO (reports bucket) 

points here. 

S3/MinIO temp prefix or local 
Temporary files during 

scratch disk, cleaned up on See Section 14.9 cleanup policy. 
processing 

completion 

S3/MinIO or Git LFS, never 
Model checkpoints Blueprint Part D: only manifest.json is versioned in git. 

committed to git directly 
Table 9.1 — CONFIRMED, synthesized from Blueprint Part F/D. 

9.2 Retention 

Retention policy for uploaded media and generated artifacts is addressed in Section 15 (Privacy & Data Retention). 

Page 21 of 63 



TrustNet AI — Master Technical Specification 

10. Authentication & Authorization 

Status:  [CONFIRMED]  — reproduced from Blueprint Part H with no audit-driven change to the design; the Audit's 
API-specification requirement (Section 11) formalizes the endpoints. 

10.1 Token design 

• Access token: short-lived JWT (e.g., 15 minutes), carries user_id and role, verified locally by every 
service/gateway without a database round-trip. 

• Refresh token: longer-lived (e.g., 7 days), stored server-side in Redis so it can be revoked; used only to mint new 
access tokens via a dedicated Auth Service endpoint. 

• Password reset [PROPOSED — not detailed in the source Blueprint excerpt; standard flow: emailed single-use 
token, short TTL, invalidates all existing refresh tokens on completion. TO VERIFY against team's final scope]. 

10.2 Roles (RBAC) 

Role Access 

Admin Full platform access, dataset management (Dataset Service admin endpoints) 

Moderator / Researcher View all scans, override flags, no user management 

User Own scans only 

Guest Rate-limited, unauthenticated demo access, if offered 
Table 10.1 — CONFIRMED, Blueprint Part H. 

10.3 Request flow 

• 1. User → Gateway over HTTPS (TLS terminated at NGINX). 

• 2. Authentication: Gateway middleware extracts and verifies the JWT locally (signature + expiry) — not a 
network call to Auth Service per request. 

• 3. Authorization (RBAC): decoded role claim checked against the route's required permission; failure returns 403 
before touching any service. 

• 4. Validation: request body validated against the route's Pydantic schema; malformed input rejected with 422 
before business logic runs. 

• 5. Routing: Gateway forwards to the internal service (sync HTTP) or publishes a broker event (async fan-out). 

• 6-8. Broker fan-out, per-service database access (own tables only), and response — as detailed in Section 2 and 
Section 7. 

CONFIRMED verbatim, Blueprint Part H. 

10.4 The one strict rule 

JWT verification logic exists in exactly one place in the codebase — shared/auth/verify_token.py — imported by every 
service's middleware. Copy-pasting token verification into five services is a guaranteed source of a security bug when 
one copy gets updated and four don't. CONFIRMED verbatim, Blueprint Part H. 

10.5 Audit logging 

Every authenticated admin action (Dataset Service writes, user role changes, manual DLQ replay) is written to the 
audit_logs collection (Section 8.2) with actor user_id, action, target, and timestamp. [PROPOSED — the Blueprint 
names audit_logs as a collection but does not enumerate exactly which admin actions must be logged; the set above is a 
reasonable default pending team confirmation.] 

Page 22 of 63 



TrustNet AI — Master Technical Specification 

11. API Specification 

Status:  [CONFIRMED + AUDIT FIX]  — sample requests/responses existed in the Blueprint's Section 7; the Audit 
requires a complete endpoint-by-endpoint table (method, auth, request, response, status codes, errors, purpose). All 
endpoints go through the Gateway and use the standard {data, error, meta} envelope (Blueprint Part O). 

11.1 Versioning 

All routes are prefixed /api/v1/. A breaking schema change bumps the major version; old and new versions are 
supported briefly during rollout — CONFIRMED, Blueprint Part O. 

11.2 Authentication endpoints 

Method & Path Auth Purpose Success / Error 

201 Created / 409 
POST /api/v1/auth/register No Create a user account 

EMAIL_EXISTS, 422 validation 

200 OK / 401 
POST /api/v1/auth/login No Issue access + refresh token 

INVALID_CREDENTIALS 

200 OK / 401 
POST /api/v1/auth/refresh Refresh token Mint a new access token 

REFRESH_TOKEN_INVALID 

POST /api/v1/auth/logout Access token Revoke the refresh token 204 No Content 

POST /api/v1/auth/password-reset Request a password-reset 202 Accepted (always, to avoid 
No 

[PROPOSED] email email enumeration) 
Table 11.1 — CONFIRMED for register/login/refresh/logout (Blueprint Part H, Section 7 sample). password-reset row is PROPOSED, TO 
VERIFY. 

11.3 Scan / upload / URL submission 

Method & Path Auth Request Response Purpose 

Create a scan for a 
URL, text, or 

{content_type, 202 {scan_id, 
uploaded media — 

POST /api/v1/scan Yes payload | file, status:"pending", 
CONFIRMED 

user_id} created_at} 
example, Blueprint 
Section 7. 

200 {scan_id, status, Poll scan progress 
GET detectors_expected[], — CONFIRMED 

Yes - 
/api/v1/orchestration/{scan_id}/status detectors_completed[], example, Blueprint 

progress_percent} Section 7. 

200 {scan_id, trust_score, Fused result — 
risk_level, confidence, CONFIRMED 

GET /api/v1/trust-score/{scan_id} Yes - 
module_scores[], example, Blueprint 
generated_at} Section 7 / Part I. 

Per-module drill-
down 
[PROPOSED — 

200 the raw 
GET implied by the 

Yes - DetectionResult (Section 
/api/v1/scan/{scan_id}/results/{module} frontend's module 

4) for one module 
breakdown 
requirement, 
Section 12]. 

Human-readable 
200 {scan_id, summary, 

GET /api/v1/explanation/{scan_id} Yes - explanation — 
evidence[]} 

CONFIRMED 

Page 23 of 63 



TrustNet AI — Master Technical Specification 

Method & Path Auth Request Response Purpose 

example, Blueprint 
Section 7. 

List the user's scan 
history — 
CONFIRMED, 

GET /api/v1/scan Yes ?status=&page= 200 {scans[], total, page} dashboard 
requirement, 
Blueprint Part H 
step 8. 

Fetch/generate a 
PDF/HTML report 

GET /api/v1/report/{scan_id} Yes - 200 {report_url} — CONFIRMED, 
Report Generation 
Service. 

Table 11.2 — rows marked CONFIRMED reproduce Blueprint Section 7 examples verbatim in tabular form; the module drill-down row is 
PROPOSED. 

11.4 Dashboard / analytics 

Method & Path Auth Purpose 

Yes (User: own 
data / Aggregated stats for the dashboard — CONFIRMED, 

GET /api/v1/analytics/summary 
Moderator+: Analytics Service responsibility, Blueprint Part C. 
platform-wide) 

GET /api/v1/notifications Yes List the user's notification log. 

11.5 Admin endpoints 

Method & Path Auth Purpose 

Dataset versioning/metadata management — 
GET/POST /api/v1/admin/dataset Admin only CONFIRMED, Dataset Service, Blueprint Part C ('Sync, 

admin-only'). 

POST /api/v1/admin/dlq/{topic}/replay Manually replay a DLQ message after root-causing a 
Admin only 

[PROPOSED] poison message (Section 6.4). 

User management [PROPOSED — implied by the Admin 
GET /api/v1/admin/users Admin only 

role's stated scope, Section 10.2]. 
Table 11.3 — the Dataset endpoint is CONFIRMED; DLQ replay and user-management endpoints are PROPOSED, following directly 
from roles/behavior already defined elsewhere in this document. 

11.6 Standard error envelope 

{ 
  "data": null, 
  "error": {"code": "SCAN_NOT_FOUND", "message": "No scan found with that id"}, 
  "meta": {"request_id": "req_9f8e7d"} 
} 

Listing 11.1 — CONFIRMED verbatim, Blueprint Section 7. 

Page 24 of 63 



TrustNet AI — Master Technical Specification 

12. Frontend Specification 

Status:  [CONFIRMED]  — React 19 + TypeScript + Tailwind CSS, per Blueprint Part R and the repository tree in 
Blueprint Section 2. 

12.1 Pages 

Page Purpose 

Login Authentication flow (Section 10). 

Dashboard Scan history table, quick upload/URL submission entry point. 

Trust score, risk level, confidence, per-module breakdown, evidence, contradiction indicators, 
ScanDetail 

partial-success indicators. 

Reports List/generate PDF reports for past scans. 

AdminPanel Admin-only: dataset management, user management (Section 11.5). 
Table 12.1 — CONFIRMED, reproduced from the pages/ folder in Blueprint Section 2's repository tree. 

12.2 Components 

Component Purpose 

Navbar Global navigation + auth state. 

File/URL/text submission with upload-progress and validation feedback (client-side mirrors 
UploadCenter 

Section 14 rules: extension/size checks before the request is even sent). 

Displays trust_score, risk_level, confidence; visually distinguishes partial=true results (Section 
TrustScoreCard 

5.4/6). 

EvidencePanel Renders evidence[] items and contradiction_flag (Section 5.3) with plain-language notes. 

ScanHistoryTable Paginated list backed by GET /api/v1/scan. 
Table 12.2 — CONFIRMED, Blueprint Section 2 repository tree, with behavior notes tying each component to the backend contracts 
defined above. 

12.3 State management & API integration 

• hooks/useAuth.ts — access/refresh token lifecycle, wraps the standard envelope. 

• hooks/useScanStatus.ts — polls GET /orchestration/{scan_id}/status at a fixed interval [PROPOSED: 2s] until 
status is terminal, then fetches GET /trust-score/{scan_id}. 

• api/client.ts, authApi.ts, scanApi.ts, reportApi.ts — thin typed wrappers, one per backend domain, matching the 
Gateway's route groups. 

• store/authStore.ts — holds the current user/session; not browser localStorage in any embedded/artifact context, 
but a normal client-side store is appropriate for the actual deployed React app. 

CONFIRMED, Blueprint Section 2 repository tree (frontend/src/hooks, api, store). 

12.4 Required UI states 

• Loading — scan submitted, awaiting detectors. 

• Partial success — some but not all detectors reported (Section 5.4); shown distinctly from a fully-complete result, 
never disguised as complete. 

• Contradiction — contradiction_flag=true surfaced explicitly (Section 5.3), not averaged into a deceptively calm-
looking score. 

Page 25 of 63 



TrustNet AI — Master Technical Specification 

• Error — scan failed entirely (Section 5.4 'no detector returned' case) shown as an explicit failure state, never a 
fabricated score. 

AUDIT FIX — the Audit specifically requires partial-success and contradiction indicators in the frontend spec; these 
states are new relative to the Blueprint's original page/component list, which named the pages but not every required 
visual state. 

12.5 Honesty constraint 

The frontend must not describe mock or placeholder functionality as implemented. Any UI element whose backing 
endpoint is PROPOSED rather than CONFIRMED (Section 11) must be built only after that endpoint exists, or clearly 
marked as a stub — never presented as a working feature during the panel demo. 

Page 26 of 63 



TrustNet AI — Master Technical Specification 

13. SSRF Protection 

Status:  [AUDIT FIX]  — the Blueprint's phishing/URL scanning flow fetches and analyzes untrusted, user-submitted 
URLs but did not document SSRF hardening in the excerpt provided. This entire section is new; every control below is 
PROPOSED engineering best practice, to be implemented in the Phishing Detection Service and the Gateway's URL-
intake path from Phase 1, not patched on at the end (Audit item 6 is explicit on this point). 

13.1 Where this lives in the architecture 

URL fetching happens inside the Phishing Detection Service's preprocessing step (feature extraction may require 
fetching page HTML per Blueprint Section E-4: 'URL string (+ optionally fetched page HTML)'). Because this is the 
one place the system deliberately makes outbound requests to attacker-influenced destinations, SSRF controls are 
placed at this single choke point rather than scattered across services. 

13.2 Controls 

Control Rule 

Only http:// and https:// are accepted. file://, ftp://, gopher://, data:// and all other schemes are 
Scheme restriction 

rejected before any resolution occurs. 

DNS resolution happens explicitly, server-side, before connecting — the resolved IP is what is 
Hostname resolution 

validated, not the hostname string alone. 

Private IP blocking Resolved IPs in RFC 1918 ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) are rejected. 

Loopback blocking 127.0.0.0/8 and ::1 are rejected. 

169.254.0.0/16 (including the cloud metadata endpoint 169.254.169.254) and fe80::/10 are 
Link-local blocking 

rejected. 

Internal network Any address the deployment environment considers internal (Docker/K8s service CIDR ranges) is 
blocking rejected via an explicit denylist, not just the public RFC 1918 ranges. 

The IP resolved at validation time is the same IP the outbound HTTP client is pinned to connect 
DNS rebinding to (connect-by-IP with the original Host header), preventing a TOCTOU DNS-rebind between 

check and fetch. 

Followed only up to a small maximum (e.g., 3); every redirect target is re-validated against every 
Redirects rule above before being followed — a redirect to a private IP is rejected exactly as a direct request 

would be. 

Ports Only 80 and 443 are permitted; arbitrary ports are rejected. 

Timeout A short connect + total-request timeout (e.g., 5s) prevents slow-loris-style resource exhaustion. 

The fetch is capped (e.g., 2 MB) and aborted if exceeded, before the full body is buffered into 
Maximum response size 

memory. 

Same cap applies to any embedded resource the analyzer chooses to follow (e.g., a linked image 
Maximum download size 

for OSINT reverse-image lookup). 

The fetcher runs with egress restricted to public internet only (no access to internal service DNS 
Sandbox / network 

names or the Docker network's internal services) — mirrors the network_configuration pattern 
isolation 

already used for this build environment. 
Table 13.1 — PROPOSED. No SSRF design was present in the source Blueprint excerpt; every row is an engineering default the team 
should review and adjust before Phase 1 sign-off (Section 28). 

13.3 Where validation happens 

All checks in Table 13.1 run inside a single shared helper (e.g., shared/net/safe_fetch.py) imported by the Phishing 
Detection Service and any future module that fetches user-influenced URLs (e.g., OSINT reverse-lookup) — following 
the same one-place, imported-everywhere discipline the Blueprint already applies to JWT verification (Section 10.4). 
Validation happens before any network connection is opened, not as a post-hoc filter on the response. 

Page 27 of 63 



TrustNet AI — Master Technical Specification 

14. Secure File Upload Pipeline 

Status:  [CONFIRMED + AUDIT FIX]  — the Blueprint names FastAPI UploadFile streaming and ClamAV (Part R); the 
Audit requires the full pipeline documented end-to-end. New controls below are PROPOSED. 

14.1 Pipeline stages, in order 

Stage Check Status 

Reject any filename whose extension is not in the modality's allow-list (e.g., 
1. Extension validation PROPOSED 

.jpg/.png/.webp for image; .wav/.mp3 for audio; .mp4/.mov for video). 

2. MIME validation The declared Content-Type must match the extension's expected MIME type. PROPOSED 

The first bytes of the file are checked against known file signatures — a 
3. Magic-byte 

renamed .exe with a .jpg extension is rejected even though extension and PROPOSED 
validation 

declared MIME both look correct. 

Per-modality maximum size (e.g., 10 MB image, 25 MB audio, 200 MB video) 
4. File-size limits [PROPOSED, TO VERIFY against actual demo hardware/GPU memory PROPOSED 

budget]. 

5. Filename The stored object key is a generated UUID, never the user-supplied filename — 
PROPOSED 

sanitization eliminates path-traversal and collision risks entirely. 

Uploads land in a quarantine prefix in Object Storage (Section 9) and are only 
6. Storage isolation PROPOSED 

promoted to the working prefix after stages 1-9 pass. 

7. Temporary file Any local scratch file used during validation/preprocessing is written to a per-
PROPOSED 

handling request temp directory and deleted immediately after use, success or failure. 

8. 
Not applicable to the modalities in scope (no zip/archive uploads are accepted) CONFIRMED 

Archive/decompression 
— explicitly out of scope rather than silently unhandled. scope limit 

protection 

Image: Pillow load + verify(); Audio: librosa/torchaudio load succeeds and 
9. Modality-specific 

duration is within bounds; Video: ffprobe metadata check before any ffmpeg PROPOSED 
validation 

processing runs. 

Video/audio processing invokes ffmpeg with an explicit, whitelisted argument 
10. FFmpeg safety set (no shell=True, no user-controlled filter strings) to prevent command PROPOSED 

injection via a crafted filename or metadata field. 

EXIF/ID3/video-container metadata is stripped or read only through a safe 
11. Metadata handling parser (never passed to a shell); it is not stored beyond what a detector's PROPOSED 

evidence explicitly needs. 

ClamAV (self-hosted, run as a sidecar via clamd) scans every upload before it CONFIRMED, 
12. Malware scanning 

is promoted out of quarantine. Blueprint Part R 

Quarantine-prefix objects that fail any check are deleted immediately; a 
13. Cleanup scheduled sweep removes any orphaned quarantine object older than a short PROPOSED 

TTL. 

Upload endpoints are subject to the same Gateway rate-limit middleware as 
14. Rate limiting PROPOSED 

every other route (Section 10.3), plus a per-user daily upload-volume cap. 
Table 14.1 — malware scanning via ClamAV is CONFIRMED from Blueprint Part R; every other stage is PROPOSED, filling a gap the 
Audit explicitly flags (item 7), since the Blueprint excerpt names FastAPI's native UploadFile handling but not the full validation sequence. 

14.2 Where validation happens 

All stages run inside the Gateway's upload-intake path and the Scan Management Service, before scan.created is ever 
published — an unvalidated file never reaches a detector's preprocessing code, and never reaches Object Storage's non-
quarantine prefix. This mirrors the SSRF choke-point pattern in Section 13: validate once, at the single entry point, not 
per-consumer. 

Page 28 of 63 



TrustNet AI — Master Technical Specification 

15. Privacy & Data Retention 

Status:  [AUDIT FIX]  — not covered in the Blueprint excerpt beyond 'what should never be stored' (Section 8.4). This 
section is new, kept strictly technical/policy-oriented; it makes no legal claims, per Audit instruction. 

15.1 What is stored, and why 

Data Why stored Where 

Account credentials 
Authentication PostgreSQL users (Section 8.1) 

(hashed) 

Object Storage, quarantine then working 
Uploaded media Input to detection pipeline 

prefix (Section 9, 14) 

DetectionResult documents Fusion input, audit trail, explainability MongoDB detection_results (Section 8.2) 

Trust score records The product's core output PostgreSQL trust_scores (Section 8.1) 

Explanations / evidence User-facing report content MongoDB explanations (Section 8.2) 

Audit / detection logs Security and debugging trail MongoDB audit_logs (Section 8.2) 

15.2 Retention 

• Uploaded media and analysis metadata are stored separately by design (Object Storage vs. databases, Section 
8.4/9) so a retention policy can delete the media independently of the scan record it belongs to. 

• Automatic deletion of uploaded media after a fixed window (e.g., 30 days) is [FUTURE / not MVP] — the MVP 
retains uploads for the duration of the demo/evaluation period only; a scheduled deletion job is a documented 
future addition, not built for Phase 0-13 (Section 28). 

• Users may request deletion of their own scans and associated media manually via the Admin/User flow 
[PROPOSED — no explicit delete endpoint exists yet in Section 11; add DELETE /api/v1/scan/{scan_id} as a 
Phase 9 item if the team adopts this]. 

15.3 Sensitive data handling 

• Uploaded media may contain personally identifiable imagery/audio (faces, voices). Access to detection_results 
and raw media is restricted to the owning user and Admin/Moderator roles (Section 10.2) — no cross-user access 
path exists in the API surface (Section 11). 

• OSINT metadata may reference external, third-party-sourced information about the content being verified; this 
data is stored in osint_metadata (Section 8.2) with the same access restrictions as the parent scan. 

15.4 Access control & logging 

All access to another user's scan data requires the Moderator/Researcher or Admin role (Section 10.2); every such 
access by a non-owner is written to audit_logs (Section 10.5). 

Page 29 of 63 



TrustNet AI — Master Technical Specification 

16. AI / ML Detection Modules 

Status:  [CONFIRMED (datasets/algorithms) + AUDIT FIX (full contract per module)]  — every dataset, algorithm, and 
metric named below is reproduced from Blueprint Parts E-1 through E-4, which already satisfy the Audit's no-invention 
rule. The Audit's contribution is requiring every module to be documented against the same 30-point checklist, which 
the tables below implement, and requiring every module's output to be expressed through the Section 3 risk_score and 
Section 4 DetectionResult contract. 

16.1 Phishing / Malicious URL Detection 

Property Detail 

Purpose / threat detected Identify URLs used for credential theft or malicious redirection. 

Input URL string, optionally fetched page HTML (Section 13 governs the fetch). 

Input format Raw string; page HTML fetched via the SSRF-safe fetcher (Section 13.3). 

Primary: PhishTank + Kaggle 'Phishing Website URLs' (~549,000 URLs, matches the BGL-
PhishNet reference paper). Baseline/fast-start: UCI Phishing Websites (~11,000 pre-extracted 

Dataset — CONFIRMED 
features). Freshness supplement: PhishTank live API. Alternative: Mendeley 'Web Page 
Phishing Detection' (~11,000 rows, 87 features). 

Dataset limitations — TO Class imbalance ~40/60 phishing/legit on the primary set, needs resampling; PhishTank live 
VERIFY API is registration- and rate-limited. 

Preprocessing Tokenize URL components, extract WHOIS/SSL metadata, clean/normalize. 

Lexical URL features + WHOIS/SSL metadata for the tabular path; raw tokens for the BERT 
Feature extraction 

path. 

Baseline model — 
Logistic Regression / Random Forest on lexical+WHOIS features. 

CONFIRMED 

LightGBM + BERT hybrid (matching BGL-PhishNet); ensemble via weighted voting. GNN 
Improved model — 

structural layer is a later upgrade, not attempted simultaneously with the baseline (Blueprint 
CONFIRMED 

Part E-2 note on implementation risk). 

Fine-tune BERT on labelled text; train LightGBM separately on tabular features; combine via 
Training pipeline 

weighted voting. 

Validation strategy — 
Stratified k-fold cross-validation, k=10, matching the reference paper. 

CONFIRMED 

Test strategy / leakage Held-out test split; domain-level split so the same domain/family never appears in both train 
prevention and test (Section 17.1). 

Output Native score: phishing probability, probability_of_positive_class. 

Conversion to risk_score risk_score = round(native_score * 100) — Section 3.2 Table 3.1 row 1. 

Confidence / evidence / Confidence from model calibration; evidence = flagged URL tokens + metadata fields 
explainability (domain_age_days, ssl_present); Section 4.2 EvidenceItem shape. 

LightGBM is fast; BERT inference is the bottleneck — sub-second target; consider ONNX 
Inference pipeline / latency 

export or DistilBERT if live-demo latency matters — CONFIRMED, Blueprint Part E-4. 

Unreachable page HTML (SSRF-blocked or timeout) — the module still returns a valid 
Failure cases 

DetectionResult using URL-only features, status=PARTIAL_SUCCESS. 

Kafka only; consumes detection.requested.url, publishes detector.phishing.completed (Section 
API / message interface 

7.2). 

Model versioning detector_id="phishing.lgbm_bert.v1"; checkpoints/manifest.json (Blueprint Part D). 

Evaluation metrics — Accuracy, Precision, Recall, F1, ROC-AUC — report all five, not accuracy alone (Blueprint 
CONFIRMED Part E-4). 

Research role / MVP status 
MVP. Build first (lowest risk, fastest to real numbers, Blueprint Part P). 

— CONFIRMED 

Page 30 of 63 



TrustNet AI — Master Technical Specification 

16.2 Scam / Fraudulent Message Detection 

Property Detail 

Purpose / threat detected Classify SMS/email/chat text as scam or legitimate. 

Input / format Raw user-typed or forwarded text. 

Primary: SMS Spam Collection (UCI, 5,574 messages, hand-labelled, 13%/87% imbalance — 
Dataset — CONFIRMED the standard baseline). Supplement: Fraudulent E-mail Corpus (~4,000+ scam emails), paired 

with the Enron Email Dataset (~500,000 emails) as the legitimate-class complement. 

Dataset limitations — TO Kaggle community scam/fraud call transcript sets vary in labelling quality per uploader — 
VERIFY verify licensing/methodology individually before use. 

Light lowercase/clean (transformers handle case reasonably well); tokenize via the model's own 
Preprocessing 

tokenizer. 

Baseline model — 
TF-IDF + Logistic Regression / Naive Bayes. 

CONFIRMED 

Improved model — 
Fine-tuned DistilBERT (lighter/faster than full BERT/RoBERTa). 

CONFIRMED 

Fine-tune DistilBERT with a classification head, cross-entropy loss with class weighting for 
Training pipeline 

imbalance. 

Held-out validation split, stratified by class (Blueprint Part E-4); sender/domain-family-aware 
Validation / test strategy 

split so the same sender never spans train/test (Section 17.1). 

Output Native score: scam/spam probability, probability_of_positive_class. 

Conversion to risk_score risk_score = round(native_score * 100) — Section 3.2 Table 3.1 row 2. 

Confidence / evidence / 
Highlighted phrases/tokens via attention weights — CONFIRMED, Blueprint Part E-4. 

explainability 

Inference / latency Very light — DistilBERT is fast enough for real-time use if ever needed — CONFIRMED. 

Empty/too-short text input — module returns status=SKIPPED with 
Failure cases 

error_code=EMPTY_INPUT rather than a fabricated score. 

API interface Kafka only; detection.requested.text -> detector.scam.completed. 

Evaluation metrics — 
Accuracy, Precision, Recall, F1 (F1 matters most given class imbalance). 

CONFIRMED 

Research role / MVP status 
MVP. Build first alongside Phishing (Blueprint Part P). 

— CONFIRMED 

16.3 Fake Review Detection 

Property Detail 

Purpose / threat detected Identify fabricated or incentivized product/business reviews. 

Input / format Review text + reviewer metadata (posting frequency, account age if available). 

Primary: Yelp Open Dataset filtered/unfiltered split (~7M reviews, Yelp's own filter as a weak 
label). Controlled baseline: Ott et al. Deceptive Opinion Spam Corpus (Cornell, 1,600 hotel 
reviews, perfectly balanced, gold-standard for early NLP work). Practical middle ground: 

Dataset — CONFIRMED 
Kaggle 'Fake Reviews Dataset' (~40,000, Amazon+Yelp combined, GPT-2-generated fakes). 
Scale option: Amazon Reviews (McAuley Lab) — TO VERIFY label engineering needed since 
it has no native fake-review label. 

Clean text; compute duplicate/near-duplicate similarity scores; extract behavioral features 
Preprocessing 

separately. 

Baseline model — 
TF-IDF + duplicate-detection heuristics + Logistic Regression. 

CONFIRMED 

Page 31 of 63 



TrustNet AI — Master Technical Specification 

Property Detail 

Improved model — SBERT embeddings + XGBoost classifier as primary path; Isolation Forest run in parallel on 
CONFIRMED behavioral features as a secondary anomaly signal feeding evidence, not the primary classifier. 

Validation / test strategy — Stratified k-fold plus a held-out cross-dataset test (train on one dataset, validate on another) to 
CONFIRMED check generalization (Blueprint Part E-4). 

Reviewer/business-family-aware split — the same reviewer or business never spans train/test 
Leakage prevention 

(Section 17.1). 

Output Native score: fake-review probability, probability_of_positive_class. 

Conversion to risk_score risk_score = round(native_score * 100) — Section 3.2 Table 3.1 row 3. 

Confidence / evidence / Which features (duplicate score, sentiment mismatch, burst pattern) drove the flag — 
explainability CONFIRMED, Blueprint Part E-4. 

Inference / latency Light — SBERT embedding + XGBoost inference is fast — CONFIRMED. 

Reviewer metadata unavailable (platform doesn't expose it) — module falls back to text-only 
Failure cases 

features, status=PARTIAL_SUCCESS. 

API interface Kafka only; detection.requested.review -> detector.review.completed. 

Evaluation metrics — Accuracy, Precision, Recall, F1, plus manual spot-check of borderline cases — fake-review 
CONFIRMED labels are inherently noisier than phishing/deepfake labels (Blueprint Part E-4). 

Research role / MVP status 
MVP. Build after Phishing/Scam Message baselines. 

— CONFIRMED 

16.4 Deepfake Detection — Image 

Property Detail 

Purpose / threat detected Detect face-swap/reenactment manipulation in a still image. 

Input / format Image file (JPEG/PNG). 

Primary: FaceForensics++ (~1.8M frames, the standard academic image/frame deepfake 
benchmark, requires signing a usage agreement — TO VERIFY access timeline). 
Generalization test: Celeb-DF v2 (~590 real + ~5,600 fake videos, harder/more realistic). Fast 

Dataset — CONFIRMED 
baseline: 140k Real and Fake Faces (Kaggle, StyleGAN+Flickr, perfectly balanced — note: 
GAN-face detection is a different task from face-swap detection, worth knowing the 
distinction). Scale-only option: DFDC — only if compute budget allows. 

Face detection + alignment/cropping (MTCNN or mediapipe); consistent resizing; 
Preprocessing normalization to backbone stats; light augmentation (flip, color jitter, compression-artifact 

simulation). 

Baseline model — 
Small CNN (ResNet-18 / EfficientNet-B0) fine-tuned on FF++ frames. 

CONFIRMED 

EfficientNet-B0 fine-tuned — matches the literature reference paper exactly, far cheaper than a 
Improved model — 

ViT from scratch. CNN chosen over ViT deliberately: a well-tuned CNN needs less data to 
CONFIRMED 

outperform a ViT at this scale (Blueprint Part E-3). 

Training pipeline ImageNet-pretrained EfficientNet-B0, standard augmentation, early stopping on validation loss. 

Validation / test strategy — Held-out split from the same dataset + a cross-dataset test (FF++ trained, Celeb-DF tested), 
CONFIRMED generalization reported honestly and separately. 

Face-identity-aware split within FF++ so the same source identity does not appear in both train 
Leakage prevention 

and test (Section 17.1). 

Output Native score: authenticity probability (probability the image is REAL). 

risk_score = round((1 - native_score) * 100) — Section 3.2 Table 3.1 row 4. This is the 
Conversion to risk_score direction the Audit explicitly calls out as a common error source (authenticity probability 

points the opposite way from a positive-class risk probability). 

Page 32 of 63 



TrustNet AI — Master Technical Specification 

Property Detail 

Confidence / evidence / 
explainability — Grad-CAM heatmap + which facial region was flagged. 
CONFIRMED 

Inference / latency — GPU strongly preferred for training; inference can run on CPU with acceptable latency for a 
CONFIRMED small (B0) model. 

No face detected in the image — status=FAILED, error_code=NO_FACE_DETECTED, rather 
Failure cases 

than a meaningless score on a non-face image. 

Kafka only; detection.requested.image -> detector.image.completed; media referenced via 
API interface 

Object Storage key (Section 9). 

Evaluation metrics — Accuracy, Precision, Recall, F1, ROC-AUC, and cross-dataset accuracy reported separately 
CONFIRMED and honestly. 

Research role / MVP status 
MVP, and the reused backbone for the Video module (16.6). 

— CONFIRMED 

16.5 Deepfake Detection — Audio 

Property Detail 

Purpose / threat detected Detect synthetic/spoofed speech (voice-cloning scam calls). 

Input / format Audio file (WAV/MP3), resampled to a consistent rate. 

Primary: ASVspoof 2019/2021 (~120,000+ utterances, the field-standard benchmark). 
Secondary, matches the architecture's vocoder-artifact sub-task: WaveFake (~100,000+ 

Dataset — CONFIRMED generated clips), paired with LJSpeech (13,100 clips, public domain) as the real-speech/bona-
fide class. AVLips — TO VERIFY, availability depends on the referenced paper's release 
terms; treat as nice-to-have only if confirmed downloadable. 

Preprocessing Consistent sample-rate resampling, silence trimming, MFCC extraction (13-40 coefficients). 

Baseline model — 
MFCC features + SVM / Random Forest. 

CONFIRMED 

Improved model — BiLSTM (2-3 layers) on MFCC/spectrogram, matching the reviewed literature paper; lighter to 
CONFIRMED train than Wav2Vec2, which is a legitimate but heavier later upgrade. 

Validation / test strategy — Held-out split, ideally cross-dataset (ASVspoof-trained, WaveFake-tested) for honest 
CONFIRMED generalization reporting. 

Leakage prevention Speaker-family-aware split — the same speaker/source never spans train/test (Section 17.1). 

Output Native score: spoof probability, probability_of_positive_class. 

Conversion to risk_score risk_score = round(native_score * 100) — Section 3.2 Table 3.1 row 5. 

Confidence / evidence / 
Per-coefficient / per-time-segment attention weights — which MFCC coefficients and time 

explainability — 
windows were most influential, mirroring the reviewed paper's approach. 

CONFIRMED 

Inference / latency — 
Light — MFCC extraction + BiLSTM inference is fast, real-time-capable. 

CONFIRMED 

Failure cases Corrupt/unreadable audio file — status=FAILED, error_code=DECODE_ERROR. 

API interface Kafka only; detection.requested.audio -> detector.audio.completed. 

Evaluation metrics — 
Accuracy, Precision, Recall, F1, ROC-AUC. 

CONFIRMED 

Research role / MVP status 
MVP. 

— CONFIRMED 

16.6 Deepfake Detection — Video 

Page 33 of 63 



TrustNet AI — Master Technical Specification 

Property Detail 

Detect manipulated video (face-swap/reenactment across frames, and lip-sync/temporal 
Purpose / threat detected 

artifacts). 

Input / format Video file (MP4, etc.). 

Same as Image (16.4): FaceForensics++ primary (temporal sequences instead of single frames 
— reuses the same access-gated dataset, saving setup effort), Celeb-DF v2 for generalization. 
DeeperForensics-1.0 (60,000 videos, controlled compression/blur perturbations) worth 

Dataset — CONFIRMED 
pursuing if FF++ alone proves too clean — TO VERIFY access. UBFC-rPPG is a feasibility-
only dataset for the rPPG sanity-check (Section 16.6, rPPG note below), never a deepfake-
classification dataset. 

Frame sampling at 1-2 fps (not every frame); face detection/tracking; consistent alignment 
Preprocessing 

across frames. 

Baseline model — 
Frame-level image classifier (reused from 16.4) applied per-frame, majority-voted. 

CONFIRMED 

Frame-level EfficientNet (reused image model) + a lightweight temporal layer (small LSTM or 
Improved model — simple moving-average/majority-vote) + blink-rate and basic lip-sync-offset heuristics. A full 
CONFIRMED spatio-temporal Vision Transformer is a legitimate but explicitly later item, not attempted first 

(Blueprint Part E-3). 

Video-level held-out split — frames from the same source video must NEVER be split across 
Validation / test strategy — 

train/test. This is flagged in the Blueprint as 'the single most common evaluation mistake in 
CONFIRMED, CRITICAL 

student deepfake-detection projects,' and is enforced project-wide in Section 17. 

Output Native score: fake probability, video-level aggregate across frame-level scores. 

risk_score = round(native_score * 100) — Section 3.2 Table 3.1 row 6 (PROPOSED direction, 
Conversion to risk_score consistent with the fake-probability convention used by the other positive-class detectors; TO 

VERIFY the video model's exact output framing once built). 

Confidence / evidence / 
Representative-frame Grad-CAM (the least-confident or most-influential frames, not every 

explainability — 
frame) + a temporal-consistency plot + blink-rate/lip-sync evidence. 

CONFIRMED 

Inference / latency — Heaviest of the three deepfake modules; frame-sampling rate directly trades off latency vs. 
CONFIRMED accuracy; most likely to need GPU at inference time. 

No faces detected in any sampled frame — status=FAILED, 
Failure cases 

error_code=NO_FACE_DETECTED, same convention as Image. 

Kafka only; detection.requested.video -> detector.video.completed; runs as its own separate 
API interface 

service, never merged with Image/Audio (Section 16.7, Blueprint Part C). 

Evaluation metrics — Video-level Accuracy, Precision, Recall, F1, ROC-AUC — always at the video level, not 
CONFIRMED frame level, since that's what a user actually cares about. 

Research role / MVP status MVP is frame-level reuse + basic temporal smoothing. Full temporal ViT and rPPG are explicit 
— CONFIRMED stretch/future items (Section 16.6.1, Section 29). 

16.6.1 rPPG constraint — AUDIT FIX 

rPPG (remote photoplethysmography, extracting a physiological pulse signal from video) is included only as a 
Research Enhancement / Stretch item, never a dependency of the video detector's basic operation. The video module's 
predict() function MUST return a valid, complete DetectionResult without rPPG under all circumstances — rPPG, if 
pursued, is an additive, non-blocking signal fused in only when successfully extracted. Validate rPPG in isolation first, 
against the UBFC-rPPG feasibility dataset (42 subjects, a physiological-signal dataset, not a deepfake dataset), before 
ever wiring it into the main video pipeline — CONFIRMED, Blueprint Part E-3, and directly satisfies Audit item 8. 

Scope tier rPPG status 

MVP Not present. Video predict() works fully without it. 

Not applicable — rPPG is Stretch/Future, not a mid-tier enhancement, per the Blueprint's explicit 
Research Enhancement 

stretch-goal classification. 

Page 34 of 63 



TrustNet AI — Master Technical Specification 

Scope tier rPPG status 

Feasibility-validated against UBFC-rPPG in isolation; wired in as an optional, non-blocking 
Stretch / Future additional evidence signal only if the isolated validation succeeds and time remains (Blueprint 

Part E-5). 

16.7 OSINT Verification Service 

Property Detail 

Cross-check submitted content against external sources (e.g., reverse image search, prior-flag 
Purpose / threat detected 

history) to corroborate or contradict the other detectors. 

Input URL, image, or text content plus metadata from the parent scan. 

No standard benchmark dataset exists for content-verification-against-external-sources — this 
is an expected literature gap. A small, hand-curated evaluation set (20-50 known-verified and 

Dataset — CONFIRMED 
known-fabricated items with documented ground truth) is used instead of searching for a 
benchmark that doesn't exist (Blueprint Part E-1 closing note). 

Preprocessing / feature Reverse-image-search query construction; metadata cross-check against external source 
extraction responses — implementation detail TO VERIFY against actual external API selection. 

Not a trained classifier in the same sense as the other six modules — a rule/scoring layer over 
Model external corroboration signals. [PROPOSED framing, since the Blueprint does not specify 

OSINT's internal scoring model beyond the service's existence and its Kafka contract.] 

Output Native score: corroboration_score, external-corroboration strength. 

risk_score = round((1 - corroboration_score) * 100) — Section 3.2 Table 3.1 row 7 
Conversion to risk_score 

(PROPOSED, low external corroboration reads as elevated risk). 

Which external source(s) were checked and what they returned; surfaced directly in 
Evidence / explainability 

contradiction cases against the Image/Video deepfake modules (Section 5.3 worked example). 

External source unreachable/rate-limited — status=PARTIAL_SUCCESS or UNAVAILABLE 
Failure cases 

(Section 6.1), never treated as 'no corroboration found = high risk' silently. 

API interface Kafka only; detection.requested.osint -> detector.osint.completed. 

Stretch/Future — full OSINT verification against multiple external sources is explicitly a 
Research role / MVP status 

stretch goal, scoped down and built last, given its external-dependency risk and lack of 
— CONFIRMED 

precedent (Blueprint Part P, Part E-5). 

Page 35 of 63 



TrustNet AI — Master Technical Specification 

17. Data Leakage Prevention 

Status:  [CONFIRMED (video) + AUDIT FIX (project-wide)]  — the Blueprint explicitly flags video frame-level leakage as 
'the single most common evaluation mistake in student deepfake-detection projects.' The Audit requires the same 
discipline applied to every modality, not just video. This section is the project-wide policy every evaluation script must 
enforce. 

17.1 Leakage risk by modality 

Modality Leakage risk Split unit 

Frames from the same source video appear in both 
Video train and test, inflating reported accuracy — Split at the video level, never the frame level. 

CONFIRMED, explicit Blueprint warning. 

The same face identity (multiple frames/images of AUDIT FIX — split at the identity level 
Image 

one person) spans train and test. within FF++/Celeb-DF. 

The same speaker's voice (bona-fide or spoofed) 
Audio AUDIT FIX — split at the speaker level. 

appears in both splits. 

AUDIT FIX — split at the sender/domain-
The same sender/template/campaign appears in both 

Text (scam family level where sender metadata exists; 
splits, letting the model memorize a specific sender's 

messages) otherwise a documented random split with 
phrasing rather than generalize. 

duplicate/near-duplicate removal. 

Phishing URLs / The same domain (or closely related domain family) AUDIT FIX — split at the domain level, not 
domains appears in both splits. the individual-URL level. 

The same reviewer or the same business/product 
listing appears in both splits, letting the model AUDIT FIX — split at the reviewer-family / 

Fake reviews 
memorize a specific reviewer's or business's writing business-family level. 
style rather than the fake/genuine signal itself. 

Tabular datasets AUDIT FIX — de-duplicate before splitting; 
Duplicate rows or near-duplicate feature vectors 

(UCI-style pre- respect any split already defined by the 
across the published train/test files. 

extracted features) dataset's authors rather than re-shuffling. 
Table 17.1 — the Video row is CONFIRMED verbatim; every other row is an AUDIT FIX extension of the same principle to the remaining 
six modalities, per Audit item 5. 

17.2 Split definition 

• TRAIN — used for model fitting only. 

• VALIDATION — used for hyperparameter selection, early stopping, and fusion-weight derivation (Section 5.2 
Step 2); never used for final reported metrics. 

• TEST — held out, touched exactly once per model version, used only for the final reported metrics in Section 19. 

Splitting occurs once per dataset version, at data-preparation time (Phase 2, Section 28), before any model training 
begins — not re-shuffled per experiment. 

17.3 Reproducible, recorded splits 

Each modality's models/<modality>/data/manifest.json (Blueprint Part D) records exactly which source IDs (video IDs, 
speaker IDs, domains, reviewer IDs, sender IDs) were assigned to each split, along with the random seed used to 
generate the split. Re-running the split script against the same manifest and seed reproduces an identical split — this is 
the artifact evaluation scripts load rather than re-deriving the split ad hoc. 

17.4 Enforcement 

Every models/<modality>/evaluation/evaluate.py script (Blueprint Part D) asserts, before computing any metric, that 
no split-unit identifier (video_id / speaker_id / domain / sender_id / reviewer_id, per Table 17.1) appears in more than 

Page 36 of 63 



TrustNet AI — Master Technical Specification 

one of TRAIN/VALIDATION/TEST for the manifest it loaded. A violation raises a hard error rather than a warning — 
CI (Section 25) runs this assertion as part of ci-models.yml (Blueprint Section 6) on every PR touching models/. 

Page 37 of 63 



TrustNet AI — Master Technical Specification 

18. Reproducibility 

Status:  [AUDIT FIX]  — the Blueprint's MLOps row (Part R) names MLflow/W&B and DVC-or-manifest but does not 
enumerate the full reproducibility artifact set. This section closes that gap. 

Artifact Where it lives Notes 

Section 17.3; which dataset release/snapshot 
Dataset version models/<modality>/data/manifest.json 

was used. 

Data manifest (split 
models/<modality>/data/manifest.json Section 17.3. 

assignment) 

preprocessing_version field, propagated into Lets a bug in preprocessing be traced to 
Preprocessing version 

every DetectionResult (Section 4) exactly which results it affected. 

Which experiment run produced the 
Model version checkpoints/manifest.json (Blueprint Part D) 

checkpoint actually shipped. 

Hyperparameters, thresholds, 
Configuration version models/<modality>/configs/model_config.yaml native_score_semantics (Section 3.3) — never 

hardcoded in Python. 

training/hyperparams.yaml and the split-
Random seeds Fixed and recorded, not left to default/unset. 

generation script's recorded seed 

Train/val/test split record manifest.json (Section 17.3) Reproducible per Section 17.3. 

Requirements / Per-service requirements.txt (Blueprint Part R 
Isolated per service, not one shared file. 

dependencies dependency-management row) 

MLflow (self-hosted) or W&B free tier — Tracks which run produced which checkpoint 
Experiment tracking 

CONFIRMED, Blueprint Part R and metrics. 

Enforces Section 17.4 leakage assertions 
Evaluation script models/<modality>/evaluation/evaluate.py 

before computing metrics. 

Posted as a CI PR comment by ci-models.yml 
Evaluation output models/<modality>/evaluation/reports/ 

(Blueprint Section 6). 

docker/base-python.Dockerfile / base- Same base image used for training and 
Environment information 

gpu.Dockerfile pinned versions inference where feasible. 
Table 18.1 — AUDIT FIX. Rows citing 'CONFIRMED' reuse an existing Blueprint decision; the table itself, as an explicit reproducibility 
checklist, is new. 

Page 38 of 63 



TrustNet AI — Master Technical Specification 

19. Research Evaluation Methodology 

Status:  [CONFIRMED (per-module metrics) + AUDIT FIX (fusion-comparison methodology)]  — the Blueprint's Part E-4 
already specifies per-module metrics honestly (Accuracy/Precision/Recall/F1/ROC-AUC, cross-dataset checks). The 
Audit requires, in addition, a structured comparison across fusion strategies using the same fixed test split. 

19.1 Evaluation tiers 

Tier What is measured Status 

A. Individual Per-module Accuracy/Precision/Recall/F1/ROC-AUC (PR-AUC and MCC 
CONFIRMED, Blueprint 

detector where class imbalance is severe, e.g., phishing and scam message) on that 
Part E-4. 

performance module's own held-out test split (Section 17). 

AUDIT FIX — a 
comparison point the 

B. Simple Unweighted average of all reporting modules' risk_scores on a fixed multi-
weighted approach must 

fusion baseline modal test set, evaluated against the same ground truth. 
beat to justify its added 
complexity. 

C. Weighted Section 5.2 Step 2 weighted average, using validation-derived weights, on AUDIT FIX, matching 
fusion the same fixed test set as Tier B. Section 5.2. 

D. Weighted 
fusion + AUDIT FIX, matching 

Section 5.2 Step 3 added on top of Tier C. 
contradiction Section 5.3. 
detection 

Table 19.1 — same fixed test split is used across B/C/D for a fair, non-cherry-picked comparison, per Audit item 10. 

19.2 Metric selection per modality 

Not every metric is forced onto every model. Classification tasks (all seven modules) report 
Accuracy/Precision/Recall/F1/ROC-AUC; PR-AUC and MCC are added specifically where class imbalance is 
significant (phishing ~40/60, scam message ~13/87 — Section 16.1, 16.2). Calibration metrics (ECE, Brier score) are 
reported for any module whose confidence field (Section 4.1) is exposed to the user as a trust signal, since a 
miscalibrated confidence is actively misleading — [PROPOSED scope: apply to all seven modules at minimum for the 
confidence field; TO VERIFY against actual time budget]. Confusion matrices are reported per module alongside the 
headline metrics. 

19.3 Reporting discipline 

All values in this document and in every evaluation report are [TO BE MEASURED] until an actual experiment 
produces them — CONFIRMED, Audit instruction; no numeric result is invented anywhere in this specification. 
Results become part of the frozen Phase 8/12 deliverable (Section 28) as real, run, and logged numbers referencing 
their MLflow/W&B run ID (Section 18). 

Page 39 of 63 



TrustNet AI — Master Technical Specification 

20. Ablation Study 

Status:  [AUDIT FIX]  — new section; the ablations below are constrained to components that actually exist in this 
architecture. 

Ablation Compares 

Without weighting vs. with Tier B (unweighted average, Section 19.1) vs. Tier C (weighted average) — isolates the 
weighting contribution of validation-derived weights. 

Without contradiction detection vs. Tier C vs. Tier D (Section 19.1) — isolates the contribution of the rule-based 
with contradiction detection contradiction layer (Section 5.2 Step 3), the Blueprint's stated most-novel component. 

Fusion computed over the six trained-classifier modules only vs. fusion including 
Without OSINT vs. with OSINT OSINT (Section 16.7) — isolates OSINT's marginal contribution, relevant given 

OSINT is a Stretch/Future module (Section 16.7, Section 29). 

The 'Baseline algorithm' vs. 'Strong algorithm' columns of Section 16 for each of the 
Baseline model vs. improved 

seven modules — quantifies the accuracy/complexity tradeoff the Blueprint already 
model, per module 

argues for qualitatively (Part E-2). 
Table 20.1 — AUDIT FIX, satisfying Audit item 11. Ablations are restricted to real architecture components; no synthetic ablation axis 
(e.g., a learned meta-model, which this project explicitly does not build — Section 5.2) is included. 

Page 40 of 63 



TrustNet AI — Master Technical Specification 

21. Research Contribution 

Status:  [CONFIRMED framing + AUDIT FIX (explicit novelty discipline)]  — reuses the Blueprint's own framing (Part I: 
'the single most novel piece... deserves to be simple and explainable') and applies the Audit's requirement that novelty 
not be overclaimed until measured. 

21.1 What is proposed as a contribution 

A confidence-aware, risk-normalized, explainable, multi-detector fusion architecture with validation-derived weighting 
and a rule-based contradiction-detection layer (Sections 3-6), applied specifically to the combination of phishing, scam-
message, fake-review, and multi-modal deepfake detection under one Trust Score. 

21.2 Distinguishing existing work from this project's contribution 

Category Content 

Each individual detector's model family (BGL-PhishNet-style phishing hybrid, DistilBERT text 
classification, SBERT+XGBoost review detection, EfficientNet+Grad-CAM image forensics, 

Existing literature 
BiLSTM-on-MFCC audio spoof detection) is drawn from precedented, cited published work — 
CONFIRMED, not claimed as novel. 

The plugin-architecture predict() contract, the DetectionResult schema (Section 4), the 
Our engineering 

universal risk_score convention (Section 3), the microservice/Kafka event design (Sections 2, 
implementation 

7) — real engineering work, not a research claim. 

The weighted-fusion + rule-based contradiction-detection combination (Section 5), evaluated 
Proposed methodological 

against the ablation plan in Section 20 — this is the one claim that requires actual experimental 
contribution 

support before being asserted as a contribution in the final report. 

A learned meta-model for fusion (explicitly deferred, Section 5.2), full multi-source OSINT 
Future work verification (Section 16.7), rPPG-augmented video detection (Section 16.6.1), 

Telegram/WhatsApp/browser-extension channels (Blueprint Part Q). 

21.3 Overclaiming discipline 

• No model is described as 'best' unless the Tier A per-module evaluation (Section 19.1) actually shows it 
outperforming the alternatives considered in Section 16. 

• No claim that the fused system is 'better than existing systems' is made without the required Tier B vs. C vs. D 
experimental comparison (Section 19.1) having actually been run. 

• The research contribution claim in Section 21.1 is written in the future/conditional voice throughout the 
codebase's documentation (docs/, README) until Section 19-20's experiments produce the numbers that support 
it — CONFIRMED, direct instruction from both source documents. 

Page 41 of 63 



TrustNet AI — Master Technical Specification 

22. Repository & Folder Structure 

Status:  [CONFIRMED]  — reproduced from Blueprint Section 2 (full tree) and Part B (folder ownership table); a 
monorepo, deliberately chosen for a four-person team per Blueprint Part B. 

22.1 Full repository tree 

trustnet-ai/ 
├── README.md                     docker-compose.yml   .env.example 
├── docker-compose.prod.yml       .gitignore            Makefile 
├── .github/workflows/            (Section 22.3, CI/CD) 
├── frontend/                     React 19 + TS (Section 12) 
│   └── src/{components,pages,hooks,api,store}/ 
├── gateway/                      FastAPI Gateway (Section 10.3) 
│   └── {routers,middleware,core,config}/ 
├── services/ 
│   ├── auth-service/              (Pattern A — REST) 
│   ├── scan-management-service/   (Pattern A — REST) 
│   ├── report-service/            (Pattern A — REST) 
│   ├── dataset-service/           (Pattern A — REST, admin-only) 
│   ├── analytics-service/         (Pattern A — REST) 
│   ├── phishing-detection-service/    (Pattern B — Kafka only) 
│   ├── scam-detection-service/        (Pattern B — Kafka only) 
│   ├── review-detection-service/      (Pattern B — Kafka only) 
│   ├── image-deepfake-service/        (Pattern B — Kafka only) 
│   ├── audio-deepfake-service/        (Pattern B — Kafka only) 
│   ├── video-deepfake-service/        (Pattern B — Kafka only) 
│   ├── osint-service/                 (Pattern B — Kafka only) 
│   ├── ai-orchestration-service/  (Pattern C — Hybrid) 
│   ├── trust-engine-service/      (Pattern C — Hybrid, Section 5) 
│   ├── explainability-service/    (Pattern C — Hybrid) 
│   └── notification-service/      (Pattern C — Hybrid) 
├── models/                       one folder per modality (Section 22.2) 
│   ├── phishing/  scam_text/  fake_review/ 
│   └── image_deepfake/  audio_deepfake/  video_deepfake/  osint/ 
├── shared/ 
│   ├── schemas/{detection_result.py, kafka_events.py}   (Section 4) 
│   ├── auth/verify_token.py                              (Section 10.4) 
│   ├── net/safe_fetch.py                                 (Section 13.3, NEW) 
│   ├── logging/logger_setup.py   constants.py   exceptions.py 
├── docker/{base-python.Dockerfile, base-gpu.Dockerfile} 
├── k8s/  (documented scaling target — Section 27.2) 
├── infra/  (Terraform, optional — out of MVP scope) 
├── scripts/{init_postgres.sql, init_mongo.js, seed_db.py, 
│           generate_test_data.py, run_all_evaluations.py} 
├── monitoring/{prometheus/, grafana/dashboards/}          (Section 24) 
├── tests/{integration/, e2e/}                              (Section 25) 
├── configs/{.env.dev.example, .env.prod.example}           (Section 23) 
└── docs/{architecture/, api-contracts/, adrs/, runbooks/}  (Section 31) 

Figure 22.1 — CONFIRMED, reproduced from Blueprint Section 2, with section cross-references added and shared/net/safe_fetch.py 
added as the concrete location of the AUDIT FIX SSRF helper (Section 13.3). 

22.2 Model folder skeleton (identical across all seven modalities) 

models/<modality>/ 
├── data/manifest.json          # Section 17.3 — split assignment, seed 
├── preprocessing/ 
├── training/{train_*.py, hyperparams.yaml} 
├── experiments/<date>_run<n>/  # Section 18 — MLflow/W&B run artifacts 
├── checkpoints/{manifest.json, *.pt / *.pkl}   # never committed raw 
├── inference/predict.py        # THE ONLY file other services import 
├── evaluation/{evaluate.py, reports/}          # Section 17.4, 19 
├── explainability/ 
└── configs/model_config.yaml   # Section 3.3 — native_score_semantics 

Page 42 of 63 



TrustNet AI — Master Technical Specification 

Figure 22.2 — CONFIRMED, Blueprint Part D. 

22.3 CI/CD workflows 

Workflow Trigger Purpose 

PR touching services/, Lint (ruff/black), Bandit static analysis, spin up 
ci-backend.yml 

gateway/, shared/ Postgres/Mongo/Redis, run pytest. 

ci-frontend.yml PR touching frontend/ Lint, type-check, unit tests. 

Download checkpoint, run evaluate.py including the Section 17.4 
ci-models.yml PR touching models/ 

leakage assertion, post metrics as a PR comment. 

docker-build.yml Merge to develop/main Build + tag + push images to GitHub Container Registry. 

deploy-staging.yml Merge to develop Auto-deploy to staging. 

deploy-prod.yml Manual trigger on main Requires GitHub Environments manual approval. 
Table 22.1 — CONFIRMED, Blueprint Section 6. 

Page 43 of 63 



TrustNet AI — Master Technical Specification 

23. Configuration Management 

Status:  [CONFIRMED]  — pydantic-settings throughout; per Blueprint Part O/R. 

• Every service reads configuration exclusively through a Settings class (pydantic-settings) — no os.environ.get() 
scattered through business logic. 

• .env.example at the repo root lists every environment variable any service needs, with a placeholder value and 
one-line comment; configs/.env.dev.example and configs/.env.prod.example hold environment-level templates. 

• models/<modality>/configs/model_config.yaml — hyperparameters, thresholds, native_score_semantics (Section 
3.3), model paths. 

• trust-engine-service/config/fusion_weights.yaml — Section 5.2 Step 2 weights, versioned alongside the 
model_version that produced them. 

• Shared schemas live in shared/schemas/, imported everywhere — never duplicated per service (Blueprint Part O). 

23.1 What must never be committed to Git 

• Secrets, tokens, passwords, private credentials, and API keys (OSINT source keys, JWT signing keys) — 
environment variables locally, Kubernetes Secrets / Docker secrets in deployment (Blueprint Part R). 

• Model checkpoints (large binaries) and raw datasets — only manifest.json files are versioned in git; binaries live 
in Object Storage (Section 9) / Git LFS if genuinely necessary (Blueprint Part D). 

• .dockerignore excludes checkpoints/, experiments/, tests/, .git from build contexts (Blueprint Part J). 

Page 44 of 63 



TrustNet AI — Master Technical Specification 

24. Observability 

Status:  [CONFIRMED]  — Prometheus + Grafana + Loki, per Blueprint Part K. No additional observability technology 
is introduced, per Audit's overengineering guardrail. 

• Structured logging: every service logs JSON with a request_id/scan_id threaded through every downstream 
broker event and service call (Section 6.7, Blueprint Part O). 

• Metrics: Prometheus scrapes /metrics on every service from week 6, not retrofitted later — request count, latency 
histograms, error rate, and for AI services, inference-time and queue-depth. 

• Dashboards (minimum viable set): system-health overview, AI-pipeline per-detector latency/throughput, broker 
consumer-lag-per-topic (the earliest bottleneck signal). 

• Centralized logs: Grafana Loki (lighter than full ELK, integrates natively with the same Grafana dashboards used 
for metrics). 

• Alerts (minimum set): any DLQ topic receiving a message (Section 6.4), any service's error rate exceeding 
threshold, any service failing its readiness probe for more than a minute. 

• Tracing: request_id / scan_id propagation (Section 6.7) is the project's tracing mechanism; a dedicated 
distributed-tracing product is not adopted, consistent with the Blueprint's 'build the observability you will actually 
look at' principle. 

Page 45 of 63 



TrustNet AI — Master Technical Specification 

25. Testing Strategy 

Status:  [CONFIRMED + AUDIT FIX]  — the Blueprint's test pyramid (Part M) is extended with the Audit's explicit 
schema-contract, broker, data-leakage, SSRF, and file-upload-security categories. 

Test layer Scope Status 

Service-layer business logic, repository-layer query correctness. Runs on CONFIRMED, 
Unit tests 

every PR. Blueprint Part M 

Precision/Recall/F1/AUC on held-out sets, re-run whenever a checkpoint 
Model tests CONFIRMED 

changes; results logged to experiments/ (Section 18). 

Broker producer -> consumer flows using a test broker/testcontainers, e.g. 
Integration tests CONFIRMED 

'publishing scan.created results in the right detection.requested events.' 

Contract-level tests against the Gateway, reusing FastAPI's generated 
API tests CONFIRMED 

OpenAPI schema to catch drift automatically. 

Every DetectionResult (Section 4) a detector publishes validates against 
Schema contract tests the shared Pydantic schema; a module that drifts from the contract fails CI AUDIT FIX 

before it ever reaches the Trust Score Engine. 

AUDIT FIX, 
extends 

DLQ routing after exhausted retries (Section 6.4); idempotency — 
Broker tests CONFIRMED 

replaying a message does not double-write a result (Section 6.5). 
integration-test 
scope 

Security tests See Section 26 (full plan). AUDIT FIX 

5-10 full-path scenarios: upload image -> expect a trust score within N 
End-to-end tests CONFIRMED 

seconds; directly validates the graceful-degradation exit criterion. 

Locust or k6 simulating concurrent scan submissions, watching broker 
Performance tests CONFIRMED 

consumer lag and API latency under load. 

CONFIRMED, 
Deliberately kill one detector mid-flow; confirm the system degrades per 

Failure / chaos-style tests Blueprint Phase 6 
Section 6's state table rather than cascading. 

exit criterion 

Section 17.4 assertion, run in ci-models.yml on every PR touching 
Data leakage tests AUDIT FIX 

models/. 

SSRF tests See Section 26. AUDIT FIX 

File upload security tests See Section 26. AUDIT FIX 

Page 46 of 63 



TrustNet AI — Master Technical Specification 

26. Security Test Plan 

Status:  [AUDIT FIX]  — the Blueprint's Part M names 'basic security checks'; the Audit requires explicit categories, 
reproduced below. 

Category Test cases 

Access a protected route with no token, an expired token, and a token signed with a different key; 
Authentication bypass 

all must return 401. 

A User-role token attempting an Admin-only route (Section 11.5) must return 403; a User 
Authorization bypass 

attempting to read another user's scan_id must return 403/404, never another user's data. 

Submit a URL resolving to 127.0.0.1, a private RFC 1918 address, the cloud metadata IP 
SSRF 

169.254.169.254, and a non-HTTP scheme; every case must be rejected per Section 13.2. 

Submit a public URL that 302-redirects to a private IP; must be rejected per Section 13.2's 
Redirect SSRF 

redirect re-validation rule. 

Upload an executable renamed with an allowed extension; magic-byte validation (Section 14.1 
Malicious upload 

stage 3) must reject it. 

Upload a file whose declared Content-Type does not match its extension; must be rejected 
Wrong MIME type 

(Section 14.1 stage 2). 

Magic-byte mismatch Same as above, verified at the byte level, independent of the declared header. 

Upload a file exceeding the modality's size limit (Section 14.1 stage 4); must be rejected before 
Oversized files 

being fully buffered. 

A crafted image/video designed to trigger a known ffmpeg/Pillow vulnerability path; validated via 
Malicious media 

the pinned, allow-listed processing invocation (Section 14.1 stage 10). 

SQL/NoSQL injection payloads through every free-text input field; must fail, since all DB access 
Injection attempts 

goes through the repository layer with parameterized queries only (Blueprint Part E). 

Rate-limit abuse Exceed the Gateway's per-user/IP rate limit (Section 10.3 middleware); must return 429. 

Redeliver an already-processed detector.<name>.completed message; must not double-write a 
Replay / idempotency 

DetectionResult or double-notify a user (Section 6.5). 

Sensitive information Error responses must never include a stack trace, internal file path, or raw exception text — only 
leakage the standard {code, message} envelope (Section 6.6). 

Table 26.1 — AUDIT FIX, satisfying Audit item 26 in full. 

Page 47 of 63 



TrustNet AI — Master Technical Specification 

27. Deployment Architecture 

Status:  [CONFIRMED]  — Docker Compose is the actual deployment; Kubernetes is the documented, validated-once 
scaling target, never made mandatory for the MVP. Preserved unchanged from Blueprint Part J, per Audit item 27's 
explicit instruction. 

27.1 Docker 

• Base image: python:3.11-slim per service; a separate CUDA-enabled base only for GPU-dependent inference 
services (image/video deepfake) — CUDA is not added to every image. 

• Multi-stage builds separate the dependency-install stage from the runtime stage. 

• .dockerignore excludes checkpoints/, experiments/, tests/, .git. 

• Every service exposes /health (liveness) and /ready (readiness, e.g. DB connection established). 

27.2 Docker Compose vs. Kubernetes — honest guidance 

Docker Compose is the correct tool for local development AND a legitimate production deployment target at this 
team's scale. Kubernetes is the correct target architecture to design for and present in diagrams, but running a real 
cluster continuously competes directly with time spent getting AI modules working. Recommended real path: build and 
demo on Docker Compose (docker-compose.prod.yml with resource limits, restart policies, health checks); have 
Kubernetes manifests written and validated once on a lightweight distribution (k3s), not run continuously. 
CONFIRMED verbatim, Blueprint Part J. 

Kubernetes concepts kept ready regardless: Ingress, ConfigMaps, Secrets, Volumes, Liveness/Readiness probes 
mapping directly to /health and /ready, and Horizontal Pod Autoscaling as the concrete answer to 'how would this scale 
to a million users' — scaling detector pods independently based on broker consumer lag or CPU, which is exactly why 
the three-separate-deepfake-services decision (Section 16.4-16.6, ADR 0003) pays off at that stage. 

27.3 Actual student deployment target 

A single VM (AWS EC2 free tier / Azure student credits / a college server) running Docker Compose for the demo, 
with the K8s path documented as the scaling story — CONFIRMED, Blueprint Part R Technology Decision Guide. 

Page 48 of 63 



TrustNet AI — Master Technical Specification 

28. Development Roadmap 

Status:  [AUDIT FIX (restructured) + CONFIRMED (task content)]  — the Audit explicitly asks for dependency-driven 
phases rather than an arbitrary week-by-week schedule. The phase objectives, tasks, and exit criteria below are 
reorganized into that shape but every task is reproduced from the Blueprint's own Part A phase list and Part P week-by-
week order — no new work is invented, only resequenced by dependency. Blueprint week numbers are retained in 
parentheses as a reference mapping, not as the governing schedule. 

Objective / What must 
Phase Tasks Deliverables / Acceptance 

Prerequisites NOT start yet 

Re-read every module's 
requirement; write one paragraph 
per module stating exact 

Phase 0 — A one-page frozen requirement doc, Do not scaffold 
input/output/'done'. Shortlist 

Architecture signed off, listing exact any service or 
 datasets (Section 16) and 

Freeze Prereq: inputs/outputs per module and the write any 
confirm they load and are legally 

None. MVP boundary. model code yet. 
usable. Freeze the MVP/Future 
boundary (Section 29) and get 
guide sign-off. 

Draw the service-boundary 
diagram (Section 2) and agree 
data ownership (Section 8). 
Write request/response contracts 
for every inter-service call Do not begin 

Phase 1 — (Section 11). Design the DB AI model 
Auth, schema (Section 8) and broker A user can register, log in, and training against 
Gateway, topic list (Section 7) on paper. create a scan record that persists — production 
Database,  Build Auth Service (JWT, zero AI models involved. docker- infra; use 
Storage RBAC, refresh) first. Build the compose up brings up all core infra notebooks/local 
Prereq: Phase Gateway's routing/auth- + stub services on every machine. data until this 
0 sign-off. check/rate-limiting middleware. phase's exit 

Build Scan Management Service. criterion is met. 
Stand up the SSRF-safe fetch 
helper (Section 13) and the 
upload pipeline skeleton (Section 
14). 

Confirm every chosen dataset 
Phase 2 — 

downloads, loads, and matches 
Dataset 

its documented label scheme. Do not train a 
Verification + 

Request access to gated datasets Every dataset has a recorded, 'strong' model 
Experiment 

 (FF++, Celeb-DF) immediately. reproducible split manifest (Section before its 
Framework 

Set up MLflow/W&B (Section 17.3); experiment tracking is live. baseline is 
Prereq: Phase 

18). Define and record the defined. 
0 dataset 

leakage-safe splits (Section 17) 
shortlist. 

for every modality. 

Build the simplest viable model 
per module (Section 16, 

Phase 3 — 'Baseline model' rows), in build Do not begin 
Every MVP module has a baseline 

Baseline order: Phishing + Scam Message the 'improved' 
model with real, logged 

Models Prereq: first (lowest risk, fastest to real model for a 
 Precision/Recall/F1/AUC numbers 

Phase 2 numbers), then Fake Review, module before 
— CONFIRMED, Blueprint Phase 

datasets/splits then Image Deepfake, then its baseline is 
4 exit criterion. 

ready. Audio Deepfake. Evaluate measured. 
honestly against Section 19 Tier 
A metrics. 

Phase 4 — Build the 'Strong algorithm' per Do not wire an 
Every MVP module's improved 

Improved module (Section 16). Video unmeasured 
model is measured and beats (or 

Models Prereq:  Deepfake begins (reuses the improved 
honestly does not beat) its baseline, 

Phase 3 Image backbone). rPPG model into the 
per Section 19 Tier A. 

baseline feasibility validated in isolation Kafka pipeline 

Page 49 of 63 



TrustNet AI — Master Technical Specification 

Objective / What must 
Phase Tasks Deliverables / Acceptance 

Prerequisites NOT start yet 

measured per only if time allows (Section ahead of its 
module. 16.6.1) — never on the video baseline. 

module's critical path. 

Phase 5 — Do not skip the 
Inference Wrap each finished model DetectionResult 
Services behind the predict() interface schema-

Every MVP module produces a 
Prereq: Phase (Section 4, Section 22.2) — a contract test 

 valid DetectionResult (Section 4) 
3 (at model that only runs in a (Section 25) for 

matching the shared schema. 
minimum) notebook is not integration- any module 
baseline per ready. before 
module. integration. 

Phase 6 — Integrate one detection service at 
Message a time, in priority order 

A real upload flows Gateway -> 
Broker (Phishing -> Scam -> Review -> Do not 

Broker -> at least three real 
Orchestration Image -> Audio -> Video -> integrate a 

detection services -> stored 
Prereq: Phase  OSINT) — never a 'big bang' fourth detector 

DetectionResult, no stubs remaining 
1 topic list, integration of all seven before the first 

in that path — CONFIRMED, 
Phase 5 at least simultaneously. Wire DLQ, three are stable. 

Blueprint Phase 5 exit criterion. 
one real retry, and idempotency per 
service. Section 6. 

Build fusion Steps 1-2 (Section 
Phase 7 — Do not attempt 

5.2) against real (not synthetic) 
Trust Score contradiction 

outputs from Phishing + Scam Trust Score Engine produces a fused 
Engine Prereq: detection with 

Message as soon as both are score from real module outputs, 
Phase 6, at  fewer than two 

integrated. Add Step 3 with the full availability matrix 
least two real independent, 

(contradiction detection) only (Section 5.4) implemented. 
modules comparable 

once three or more modules are 
integrated. signals. 

live. 

Do not hand-
Phase 8 — 

write example 
Explainability Build the Explainability Service's 

GET /explanation/{scan_id} returns explanations 
Prereq: Phase aggregation/templating logic 

 a real, non-mocked human-readable into the 
7 fusion (Section 5.5) over real evidence[] 

summary. frontend ahead 
producing real lists. 

of the real 
scores. 

service. 

Phase 9 — Do not present 
Wire the pages/components 

Frontend a stubbed 
(Section 12) to real endpoints 

Integration The frontend never describes mock detector's 
(Section 11), replacing any stub 

Prereq: Phase  functionality as implemented output as a 
data. Implement partial-success 

6-8 producing (Section 12.5). finished feature 
and contradiction UI states 

real backend in any demo 
(Section 12.4). 

data. build. 

Do not treat 
Phase 10 — manual, one-off 

Run the Section 26 security test 
Security testing as 

plan end-to-end: auth/authz 
Verification Every category in Table 26.1 has a sufficient — 

 bypass, SSRF, malicious upload, 
Prereq: Phase passing automated test in CI. tests must be 

injection, rate-limit abuse, 
6 upload/SSRF automated and 

replay. 
paths live. re-run on every 

relevant PR. 

Do not enter 
Phase 11 — Run the complete pyramid The system's core demo path 

Phase 13 
Full Testing (Section 25): unit, integration, survives one service restart, one bad 

deployment 
Prereq: Phases API, schema-contract, broker, file upload, and 20 concurrent scan 

 before this exit 
1-10 security, end-to-end, requests without crashing — 

criterion is 
substantially performance, chaos-style, data- CONFIRMED, Blueprint Phase 6 

demonstrably 
complete. leakage tests. exit criterion. 

true. 

Page 50 of 63 



TrustNet AI — Master Technical Specification 

Objective / What must 
Phase Tasks Deliverables / Acceptance 

Prerequisites NOT start yet 

Phase 12 — 
Research Run the full Section 19 

Do not cherry-
Experiments evaluation (Tiers A-D) and the A numbers table 

pick a favorable 
Prereq: Phase Section 20 ablation study on the (Accuracy/Precision/Recall/F1/AUC 

test split or 
4 improved  fixed test splits. Record every per module, plus the Tier B/C/D 

omit an 
models result as [MEASURED], never fusion comparison) is finalized and 

unfavorable 
measured; invented, with its MLflow/W&B reproducible. 

ablation result. 
Phase 7 fusion run ID. 
live. 

Kubernetes is 
Containerize every service; write never the only 

Phase 13 — A fresh machine can deploy the full 
docker-compose.prod.yml with documented 

Deployment stack from the git repository alone, 
resource limits/restart deployment 

Prereq: Phase  following only the README — 
policies/health checks; write and path — Docker 

11 testing exit CONFIRMED, Blueprint Phase 7 
validate-once the Kubernetes Compose must 

criterion met. exit criterion. 
manifests on k3s (Section 27). work 

standalone. 
Table 28.1 — restructured per Audit item 28 into dependency order; every task/deliverable is reproduced or directly derived from 
Blueprint Part A and Part P. Original Blueprint week ranges are retained in the rightmost reference column of the source list above for 
cross-checking against the original schedule, not shown as a table column here for width reasons — see the per-phase notes in the 
paragraph list following this table. 

Phase 0 (Blueprint Weeks 1-2) — Architecture Freeze: A one-page frozen requirement doc, signed off, listing exact 
inputs/outputs per module and the MVP boundary. 

Phase 1 (Blueprint Weeks 3-8) — Auth, Gateway, Database, Storage: A user can register, log in, and create a scan 
record that persists — zero AI models involved. docker-compose up brings up all core infra + stub services on every 
machine. 

Phase 2 (Blueprint Weeks 1-2, extended) — Dataset Verification + Experiment Framework: Every dataset has a 
recorded, reproducible split manifest (Section 17.3); experiment tracking is live. 

Phase 3 (Blueprint Weeks 6-11) — Baseline Models: Every MVP module has a baseline model with real, logged 
Precision/Recall/F1/AUC numbers — CONFIRMED, Blueprint Phase 4 exit criterion. 

Phase 4 (Blueprint Weeks 8-14) — Improved Models: Every MVP module's improved model is measured and beats (or 
honestly does not beat) its baseline, per Section 19 Tier A. 

Phase 5 (Blueprint Phase 4 note) — Inference Services: Every MVP module produces a valid DetectionResult (Section 
4) matching the shared schema. 

Phase 6 (Blueprint Weeks 12-16) — Message Broker Orchestration: A real upload flows Gateway -> Broker -> at least 
three real detection services -> stored DetectionResult, no stubs remaining in that path — CONFIRMED, Blueprint 
Phase 5 exit criterion. 

Phase 7 (Blueprint Part I build order) — Trust Score Engine: Trust Score Engine produces a fused score from real 
module outputs, with the full availability matrix (Section 5.4) implemented. 

Phase 8 (Blueprint Part I) — Explainability: GET /explanation/{scan_id} returns a real, non-mocked human-readable 
summary. 

Phase 9 (Blueprint Weeks 12-16, Part Q) — Frontend Integration: The frontend never describes mock functionality as 
implemented (Section 12.5). 

Phase 10 (Blueprint Phase 6) — Security Verification: Every category in Table 26.1 has a passing automated test in CI. 

Phase 11 (Blueprint Weeks 15-17) — Full Testing: The system's core demo path survives one service restart, one bad 
file upload, and 20 concurrent scan requests without crashing — CONFIRMED, Blueprint Phase 6 exit criterion. 

Page 51 of 63 



TrustNet AI — Master Technical Specification 

Phase 12 (Blueprint Weeks 19-20, Part E-5) — Research Experiments: A numbers table 
(Accuracy/Precision/Recall/F1/AUC per module, plus the Tier B/C/D fusion comparison) is finalized and reproducible. 

Phase 13 (Blueprint Week 18) — Deployment: A fresh machine can deploy the full stack from the git repository alone, 
following only the README — CONFIRMED, Blueprint Phase 7 exit criterion. 

Page 52 of 63 



TrustNet AI — Master Technical Specification 

29. MVP / Research Enhancement / Future Classification 

Status:  [CONFIRMED]  — reproduced from Blueprint Part E-5's explicit MVP/Stretch/Future recommendation; the 
Audit requires it formalized as a single table, done below, with no feature silently moved between tiers. 

Feature MVP Research Enhancement Stretch / Future 

Phishing detection (baseline + 
Yes GNN structural layer — 

hybrid) 

RoBERTa upgrade, 
Scam message detection Yes SentenceTransformer — 

similarity 

Reviewer-behavior graph 
Fake review detection Yes — 

features 

PRNU/ELA forensic feature 
Image deepfake detection Yes — 

fusion 

Audio deepfake detection Yes Wav2Vec2 fine-tuning — 

Video deepfake (frame-level reuse + 
Yes — Full temporal ViT 

basic temporal) 

Yes — feasibility-validated only 
rPPG signal (video) No No 

(Section 16.6.1) 

Trust Score Engine v1 (weighted 
Yes — — 

average fusion) 

Yes — added once 3+ modules are 
Contradiction detection — — 

live (Section 5.2) 

Basic Explainable AI output Yes — — 

Core dashboard Yes — — 

Full OSINT (multi-source external 
— — Yes (Section 16.7) 

verification) 

Yes; Docker Compose is sufficient 
Full Kubernetes deployment — — 

for MVP (Section 27) 

Telegram/WhatsApp/Email/browser-
Yes — designed for structurally, 

extension/mobile/enterprise-API — — 
none built (Blueprint Part Q) 

channels 

Automatic media deletion / retention 
— — Yes (Section 15.2) 

job 
Table 29.1 — CONFIRMED, Blueprint Part E-5 and Part Q. 

Page 53 of 63 



TrustNet AI — Master Technical Specification 

30. Risk Register 

Status:  [CONFIRMED + AUDIT FIX]  — every existing risk from Blueprint Part N is preserved unchanged; three Audit-
identified risks (SSRF, data leakage, calibration drift) are appended, not substituted. 

Risk Likelihood Severity/Impact Impact detail Mitigation Detection Owner 

Services call each other 
only over HTTP or the 

Tight Code 
broker, never by 

coupling Broken independent review / CI Whole 
Med Med importing another 

between deployability import- team 
service's code; a CI check 

services linter 
can catch cross-service 
imports. 

Resolved at Phase 1 
(Section 28) by clear 
single ownership per data 

Circular Deadlocked type (Section 8); Architecture Backend 
Low Med 

dependencies integration recurrence signals a review lead 
service boundary drawn 
wrong, not a code 
problem. 

The predict() interface 
Model Coupled 

contract (Section 4, 22.2) Code AI/ML 
replacement Low Med inference/orchestration 

exists specifically to review lead 
difficulty code 

prevent this. 

Only GPU-dependent 
Huge Docker services use a CUDA 

Slower CI, slower CI build- DevOps 
images / slow Med Low base image; multi-stage 

onboarding time metric lead 
builds builds; shared cached 

base layers. 

Anything AI-inference-
related is async via the Latency 

Slow API Backend 
Med Med Poor demo experience broker; the user gets an dashboard 

responses lead 
immediate 'scan created' (Section 24) 
response. 

Orchestration tracks 
expected-vs-received 

Race Incorrect/partial trust count in Redis; fusion Integration 
AI/ML 

conditions in Med High scores presented as only triggers once tests 
lead 

fusion final complete or a timeout (Section 25) 
fires, clearly flagged 
partial (Section 5.4, 6.3). 

Consumer group 
monitoring (lag alerts), 

Broker Grafana 
DLQ for poison messages DevOps 

consumer Med High Silently stalled scans alert 
(Section 6.4), health- lead 

failures (Section 24) 
checked auto-restarting 
consumers. 

Sensible TTLs on all 
cached values; never 

Cache Stale phishing score Manual Backend 
Low Low cache longer than the 

inconsistency served spot-check lead 
underlying signal stays 
valid. 

Additive-first migrations, 
Database run as a separate CI/CD CI 

Backend 
migration Med Med Broken deploy step before new code migration 

lead 
problems deploys, tested against step 

real-shape data. 

Page 54 of 63 



TrustNet AI — Master Technical Specification 

Risk Likelihood Severity/Impact Impact detail Mitigation Detection Owner 

Strict Pydantic validation, 
malware scanning on 

Security Security test 
upload (Section 14), Whole 

vulnerabilities Med High Data breach / injection plan 
parameterized queries team 

(general) (Section 26) 
only, dependency 
scanning in CI. 

shared/ code kept 
Version 

minimal; each service has CI 
conflicts Whole 

Low Low Broken builds its own requirements.txt, dependency 
across team 

not one giant shared check 
services 

dependency file. 

Explicit teardown after 
Memory 

each inference call; 
leaks in long- Load test AI/ML 

Med Med OOM crash mid-demo memory profiling during 
running AI (Section 25) lead 

load testing (Section 25, 
services 

Phase 11). 

CPU-fallback mode for 
local dev 
(smaller/quantized 

GPU Dev-
models or mocked DevOps 

dependency / High Med Blocked local dev environment 
inference); GPU only lead 

availability check 
required in 
training/deployed-
inference environments. 

Full SSRF control set 
(Section 13): SSRF 

SSRF via Internal 
scheme/hostname/private- security Backend 

URL/media Med High network/metadata 
IP/redirect validation at a tests lead 

fetching exposure 
single choke point, from (Section 26) 
Phase 1. 

ci-
Project-wide split-unit 

Data leakage models.yml 
Invalid research discipline (Section 17) 

inflating leakage AI/ML 
High High claims, indefensible in enforced by an automated 

reported assertion lead 
a viva assertion in every 

accuracy (Section 
evaluation script and CI. 

22.3) 

Calibration Calibration metrics 
drift (ECE/Brier, Section 19.2) 

Model 
(confidence Users trust an tracked per model version 

evaluation AI/ML 
field becomes Med Med overconfident or in MLflow/W&B 

reports lead 
misleading underconfident score (Section 18); re-checked 

(Section 18) 
over whenever a model is 
time/versions) retrained. 

Table 30.1 — the first thirteen rows are CONFIRMED verbatim from Blueprint Part N (columns reorganized into 
Risk/Likelihood/Severity/Impact/Mitigation/Detection/Owner/Status per Audit item 31's required format; qualitative Med/High ratings are 
PROPOSED since the Blueprint's original table did not score likelihood/severity numerically). The final three rows — SSRF, data leakage, 
calibration drift — are AUDIT FIX additions, satisfying Audit item 31's explicit requirement that these three risks be added without 
deleting any existing, valid risk. 

Page 55 of 63 



TrustNet AI — Master Technical Specification 

31. Architecture Decision Records (ADRs) 

Status:  [CONFIRMED]  — ADRs 0001-0003 are reproduced from Blueprint Section 8; ADR 0004-0005 are AUDIT 
FIX additions formalizing decisions this specification made explicit in Sections 3 and 5. 

ADR 0001: Message broker choice — Kafka vs. RabbitMQ 

Status: Accepted 

Context: The system needs async fan-out from Scan Management to multiple independent detector services, with at-
least-once delivery and consumer-group semantics. 

Decision: Use RabbitMQ for the actual build; document Kafka as the target production architecture in 
diagrams (Section 7). 

Reasoning: Kafka's operational overhead (partition management, consumer-group rebalancing) is real learning-curve 
cost for a four-person team with a fixed deadline. RabbitMQ gives the same event-driven decoupling pattern with a 
simpler mental model. Event contracts (topic names, payload schemas) are broker-agnostic, so switching later is a 
config change, not a redesign. 

Consequences: Faster time-to-working-integration in Phase 6 (Section 28); the panel defense presents Kafka as the 
scaling target with RabbitMQ named explicitly as the pragmatic substitute actually running. 

ADR 0002: Docker Compose vs. Kubernetes 

Status: Accepted 

Context: The system needs a demoable, repeatable deployment procedure within the team's timeline and operational 
capacity. 

Decision: Docker Compose for the actual deployment (Section 27.3); Kubernetes manifests written and validated 
once on k3s, not run continuously. 

Reasoning: A working K8s cluster adds ingress/secrets/PVC operational overhead that competes directly with AI-
module development time. 'Here is what we run, here is what we've designed and validated as the scaling path' is a 
stronger, more honest answer than a half-working cluster on demo day. 

Consequences: Kubernetes is never presented as the only deployment path; it remains the documented scaling story 
(Section 27.2). 

ADR 0003: Modular monolith vs. full microservices 

Status: Accepted 

Context: Sixteen logical services (Section 1.4) is architecturally correct but operationally heavy for four students in one 
build cycle. 

Decision: Sixteen logical services as separate Python packages with clean interfaces from day one; deployed as 3-
4 process groups for the MVP (a 'modular monolith' per group); split into per-service containers only once 
integration is stable (Stage 2, post-MVP). 

Reasoning: A microservice boundary is a deployment/scaling boundary, not a code-organization boundary — the 
isolation/testability benefit comes from clean module interfaces regardless of container count. Splitting later is 
mechanical because broker-based communication doesn't care whether the consumer is in-process or a separate pod. 

Consequences: The panel sees a team that understands why microservices exist, not one cargo-culting the pattern. 

ADR 0004: Universal risk_score direction convention 

Status: Accepted 

Page 56 of 63 



TrustNet AI — Master Technical Specification 

Context: Different detectors' native outputs point in different semantic directions (e.g., a phishing-positive probability 
vs. an authenticity-positive probability) — fusing them without a shared convention silently averages incompatible 
signals. 

Decision: Every detector converts its native output to a fixed risk_score in [0,100], where 0 = safest and 100 = 
most suspicious, inside its own inference/predict.py wrapper, before publication (Section 3). 

Reasoning: This is the single most important correctness guardrail in the fusion architecture; getting it wrong produces 
a fused score that looks plausible but is silently backwards for one or more contributing modules. Enforcing the 
conversion at the source (each detector), rather than at the fusion engine, means the Trust Score Engine's own logic 
stays simple and auditable. 

Consequences: Every new detector added to the system inherits this obligation automatically via the shared 
DetectionResult schema (Section 4) — a missing or out-of-range risk_score fails schema validation rather than silently 
entering fusion. 

ADR 0005: Deterministic weighted-average fusion for v1 (no learned meta-model) 

Status: Accepted 

Context: A learned meta-model for fusion is a legitimate, more powerful alternative to a weighted average, but requires 
its own training data, its own risk of overfitting to a small multi-modal test set, and its own explainability burden. 

Decision: V1 fusion is a deterministic, validation-derived weighted average (Section 5.2); a learned meta-model 
is explicitly out of scope unless the source documents require it, which they do not. 

Reasoning: A weighted average is auditable in a viva, requires no additional training data, and is a legitimate, 
implementable v1 per the Blueprint's own explicit statement. Overengineering the fusion layer before the simple 
version is measured risks delivering nothing that works. 

Consequences: Ablation Tier B vs. C (Section 20) exists specifically to demonstrate the weighted average's value over 
a naive unweighted average, which is the honest bar this design must clear before any future meta-model work is 
justified. 

Page 57 of 63 



TrustNet AI — Master Technical Specification 

32. Requirements Traceability Matrix 

Status:  [AUDIT FIX]  — new; allows verification that every major requirement is actually implemented and tested. A 
representative set of top-level requirements is traced below; the team should extend this table as implementation 
proceeds. 

Requiremen Module(s Researc
Service(s) API Database Test 

t ) h eval 

Detect Model test, 
phishing-detection- POST /scan, GET MongoDB Tier A 

phishing 16.1 schema-
service /scan/{id}/results/phishing detection_results (19.1) 

URLs contract test 

Detect scam scam-detection- POST /scan, GET MongoDB 
16.2 Model test Tier A 

messages service /scan/{id}/results/scam_message detection_results 

Detect fake review-detection- POST /scan, GET MongoDB 
16.3 Model test Tier A 

reviews service /scan/{id}/results/fake_review detection_results 

Model test, 
POST /scan, GET MongoDB Tier A, 

Detect image image-deepfake- no-face-
16.4 /scan/{id}/results/image_deepfak detection_results cross-

deepfakes service detected 
e , S3 media dataset 

failure case 

MongoDB Tier A, 
Detect audio audio-deepfake- POST /scan, GET 

16.5 detection_results Model test cross-
deepfakes service /scan/{id}/results/audio_deepfake 

, S3 media dataset 

Model test, 
MongoDB video-level Tier A, 

Detect video video-deepfake- POST /scan, GET 
16.6 detection_results split cross-

deepfakes service /scan/{id}/results/video_deepfake 
, S3 media assertion dataset 

(17.4) 

Universal Schema-
3, ADR 

risk score every detector service n/a (internal contract) n/a contract test n/a 
0004 

direction (25) 

Integration 
Fuse detector 

test, Tier 
outputs into PostgreSQL 

5 trust-engine-service GET /trust-score/{scan_id} availability- B/C/D 
one Trust trust_scores 

matrix unit (19.1) 
Score 

tests (5.4) 

Handle 
GET /trust-score/{scan_id} PostgreSQL Fusion unit Ablation 

contradictory 5.3 trust-engine-service 
(contradiction_flag) trust_scores test (20) 

results 

Degrade 
ai-orchestration-

gracefully on GET Redis in-flight Chaos-style 
6 service, trust-engine- n/a 

detector /orchestration/{scan_id}/status state test (25) 
service 

failure 

Prevent SSRF 
phishing-detection-

SSRF via 13 POST /scan (content_type=url) n/a security n/a 
service, Gateway 

URL fetch tests (26) 

S3/MinIO File-upload 
Secure file 

14 Gateway, Scan Mgmt POST /scan (multipart) quarantine + security n/a 
upload 

working prefix tests (26) 

Prevent every model's Data Tiers A-
manifest.json 

train/test 17 evaluation/evaluate.p n/a leakage D depend 
(18) 

leakage y tests (25) on this 

Explain 
results in MongoDB Integration 

4.2, 5.5 explainability-service GET /explanation/{scan_id} n/a 
plain explanations test 
language 

Page 58 of 63 



TrustNet AI — Master Technical Specification 

Requiremen Module(s Researc
Service(s) API Database Test 

t ) h eval 

Authenticate Authn/auth
auth-service, POST /auth/login, /register, PostgreSQL 

and authorize 10 z bypass n/a 
Gateway /refresh users, roles 

users tests (26) 
Table 32.1 — AUDIT FIX. This is a representative starting matrix, not exhaustive; it should be extended with one row per requirement as 
the team's frozen requirement doc (Phase 0, Section 28) is finalized. 

Page 59 of 63 



TrustNet AI — Master Technical Specification 

33. Implementation Acceptance Checklist 

Status:  [AUDIT FIX]  — usable directly by the development team as a sign-off checklist. 

Architecture 

• ☐ Every module in Section 1.4 has a corresponding documented section in Section 16. 

• ☐ Every documented module in Section 16 appears in the architecture diagram (Section 2.1). 

• ☐ Three deepfake services (image/audio/video) remain separate, per ADR 0003 / Section 16.4-16.6. 

Security 

• ☐ SSRF protection (Section 13) implemented at the Gateway/URL-intake layer, not patched on later. 

• ☐ File-upload validation (Section 14) runs before any file reaches a detector's preprocessing code. 

• ☐ All Section 26 security test categories have automated, passing tests in CI. 

Authentication 

• ☐ JWT verification exists in exactly one shared module (Section 10.4), imported everywhere. 

• ☐ RBAC roles (Section 10.2) enforced at the Gateway before any service is reached. 

Database 

• ☐ Every table/collection has exactly one owning service (Section 8). 

• ☐ No raw media, plaintext secrets, or model checkpoints are stored in any database (Section 8.4). 

Storage 

• ☐ Uploads land in a quarantine prefix and are promoted only after passing all Section 14 checks. 

Datasets 

• ☐ Every dataset used is CONFIRMED against Section 16 or explicitly TO VERIFY before training begins. 

• ☐ Every dataset has a recorded, reproducible split manifest (Section 17.3). 

Preprocessing 

• ☐ preprocessing_version is recorded and propagated into every DetectionResult (Section 4, 18). 

Models 

• ☐ Every module has a measured baseline before its improved model is started (Section 28, Phase 3/4). 

• ☐ Every model's native_score_semantics and conversion formula is declared in its model_config.yaml (Section 
3.3). 

Training 

• ☐ Random seeds are fixed and recorded for every training run (Section 18). 

Evaluation 

• ☐ Section 17.4's leakage assertion passes for every modality before any metric is reported. 

• ☐ Tiers A-D (Section 19.1) and the ablation study (Section 20) are run on the same fixed test split. 

Page 60 of 63 



TrustNet AI — Master Technical Specification 

Inference 

• ☐ Every detector exposes exactly one predict(input) -> DetectionResult function (Section 4, 22.2). 

• ☐ The video detector's predict() returns a complete result without rPPG under all circumstances (Section 16.6.1). 

Schemas 

• ☐ Every published DetectionResult validates against the shared Pydantic schema (Section 4, schema-contract 
tests, Section 25). 

Broker 

• ☐ Retry (3x exponential backoff), DLQ, and idempotency (scan_id+module key) implemented per Section 6. 

• ☐ RabbitMQ is the actual running broker; Kafka is documented, never made mandatory for the MVP (Section 
7.4, ADR 0001). 

Fusion 

• ☐ The full detector-availability matrix (Section 5.4) is implemented and unit-tested, including the 'no detector 
returned' case producing no fabricated score. 

Contradiction detection 

• ☐ Implemented only after 3+ modules are live, per the build order in Section 5.2 Step 3 / Section 28 Phase 7. 

Explainability 

• ☐ GET /explanation/{scan_id} (Section 11.3) returns real, non-mocked content sourced from Section 4.2 
evidence lists. 

Frontend 

• ☐ Partial-success and contradiction UI states implemented (Section 12.4). 

• ☐ No mock functionality is presented as implemented in the demo build (Section 12.5). 

Testing 

• ☐ Every layer in Table 25.1 has passing, automated coverage before Phase 13 deployment. 

Observability 

• ☐ Prometheus /metrics live on every service since Phase 1; the three minimum Grafana dashboards exist (Section 
24). 

Deployment 

• ☐ docker-compose.prod.yml deploys the full stack from a fresh machine using only the README (Section 
27.3). 

• ☐ Kubernetes manifests exist and have been validated once on k3s, but are not the only documented path 
(Section 27.2). 

Documentation 

• ☐ This specification, the API contracts (Section 11), and all ADRs (Section 31) live in docs/ and are kept current 
as decisions change. 

Research experiments 

Page 61 of 63 



TrustNet AI — Master Technical Specification 

• ☐ All reported metrics are [MEASURED] with an MLflow/W&B run ID, never invented (Section 19.3). 

• ☐ The research contribution claim (Section 21) is stated only after Tiers B-D (Section 19.1) actually demonstrate 
it. 

Page 62 of 63 



TrustNet AI — Master Technical Specification 

Appendix A — Glossary 

Term Meaning 

risk_score Universal 0-100 score, 0=safest, 100=most suspicious (Section 3). 

DetectionResult The standard schema every detector publishes (Section 4). 

Trust Score The fused, final 0-100 output of the Trust Score Engine (Section 5). 

contradiction_flag Boolean set when two or more modules disagree sharply (Section 5.3). 

Flag indicating a trust score was computed from fewer than the expected set of detectors 
partial=true 

(Section 5.4). 

CONFIRMED / AUDIT FIX / 
PROPOSED / TO VERIFY / Status tags defined in Document Conventions, front matter. 
FUTURE 

MVP Minimum viable product scope — Section 29. 

ADR Architecture Decision Record — Section 31. 

 

Page 63 of 63