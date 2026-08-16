TrustNet AI — Engineering Blueprint 

TrustNet AI 

Enterprise Engineering Blueprint 

Software Design Document · Solution Architecture Document · Infrastructure Design Document · Developer Handbook 

A. P. Shah Institute of Technology — Department of Information Technology 

Group B10 · BE IT, Semester VII, 2026-27 · Guide: Prof. Jayshree Jha 
Nirmala Patole · Alok Sahoo · Apoorva Puranik · Vaibhavi Naik 

  

Page 1 of 48 



TrustNet AI — Engineering Blueprint 

 
How to Use This Document ....................................................................................................................................................... 4 

Part A — Development Lifecycle (Phase 0 to Phase 8) ........................................................................................................... 4 

Phase 0 — Research & Requirement Freeze (Weeks 1-2) .................................................................................................. 4 

Phase 1 — Architecture & Contracts (Weeks 3-4) ............................................................................................................. 4 

Phase 2 — Repository & Skeleton Scaffolding (Week 5) ................................................................................................... 5 

Phase 3 — Backend Core Services (Weeks 6-8) .................................................................................................................. 5 

Phase 4 — AI Model Development (Weeks 6-14, parallel to Phase 3/5) ........................................................................... 5 

Phase 5 — Integration (Weeks 12-16) .................................................................................................................................. 5 

Phase 6 — Testing & Hardening (Weeks 15-17) ................................................................................................................. 6 

Phase 7 — Deployment (Week 18)........................................................................................................................................ 6 

Phase 8 — Documentation, Demo Prep & Scaling Story (Weeks 19-20) .......................................................................... 6 

Part B — Repository & Folder Structure ................................................................................................................................ 6 

Root-level files ........................................................................................................................................................................ 7 

Part C — Microservice Architecture ....................................................................................................................................... 7 

How many services, and why ................................................................................................................................................ 7 

Service Directory.................................................................................................................................................................... 8 

Should Image, Audio, and Video be one service or three? ................................................................................................. 8 

One combined 'DeepScan' service (rejected for production, acceptable for early MVP) ........................................... 9 

Three separate services (recommended target, and worth building this way once Phase 4 starts) ............................ 9 

Part D — AI Model Organization & Plugin Architecture ..................................................................................................... 9 

Folder layout under models/ ................................................................................................................................................. 9 

Plugin architecture: build image first, add the rest without rewriting ........................................................................... 10 

Part E — Backend Architecture (per-service FastAPI layout) ............................................................................................ 10 

Request flow through the layers (within one service) ....................................................................................................... 11 

Part F — Database Design ...................................................................................................................................................... 11 

What goes where, and why .................................................................................................................................................. 11 

PostgreSQL — relational core ........................................................................................................................................ 11 

MongoDB — flexible, high-volume documents ............................................................................................................. 12 

Redis — ephemeral, hot-path data ................................................................................................................................. 12 

What should never be stored in any of these ................................................................................................................. 12 

Scaling notes ..................................................................................................................................................................... 12 

Part G — Kafka Event Architecture ..................................................................................................................................... 13 

When to use Kafka, and when not to ................................................................................................................................. 13 

Topic list ............................................................................................................................................................................... 13 

Reliability mechanics ........................................................................................................................................................... 13 

Part H — API Gateway, Request Flow & Authentication ................................................................................................... 14 

Request flow, step by step ................................................................................................................................................... 14 

Authentication design .......................................................................................................................................................... 14 

Part I — Explainable AI & Trust Score Engine ................................................................................................................... 15 

Standardized explainability output .................................................................................................................................... 15 

Trust Score Engine — fusion architecture ........................................................................................................................ 15 

Page 2 of 48 



TrustNet AI — Engineering Blueprint 

Part J — Deployment Architecture ........................................................................................................................................ 16 

Docker ................................................................................................................................................................................... 16 

Docker Compose vs. Kubernetes — honest guidance ....................................................................................................... 16 

Kubernetes concepts to have ready regardless .................................................................................................................. 16 

Part K — Monitoring & Observability .................................................................................................................................. 17 

Part L — Git Strategy & Team Workflow (4 members) ...................................................................................................... 17 

Part M — Testing Strategy ..................................................................................................................................................... 17 

Part N — Risk Register ........................................................................................................................................................... 18 

Part O — Coding Standards ................................................................................................................................................... 19 

Part P — Development Order & Week-by-Week Roadmap ............................................................................................... 19 

Part Q — Designing for Future Channels (Telegram, WhatsApp, Email, Browser Extension, Mobile, Enterprise API)
 ................................................................................................................................................................................................... 20 

Part E-1 — Datasets Per Module ........................................................................................................................................... 20 

1. Phishing / Malicious URL Detection .............................................................................................................................. 21 

2. Scam Message Detection.................................................................................................................................................. 21 

3. Fake Review Detection .................................................................................................................................................... 21 

4. Deepfake Detection — Image .......................................................................................................................................... 22 

5. Deepfake Detection — Audio .......................................................................................................................................... 23 

6. Deepfake Detection — Video .......................................................................................................................................... 23 

Part E-2 — Algorithm Recommendations Per Module ........................................................................................................ 24 

Part E-3 — Deepfake Architecture Depth: Image, Audio, Video ........................................................................................ 25 

Image ..................................................................................................................................................................................... 25 

Audio ..................................................................................................................................................................................... 25 

Video ..................................................................................................................................................................................... 26 

Part E-4 — Per-Model Input/Pipeline/Deployment Summary ............................................................................................ 26 

Part E-5 — Research Roadmap & Overall Strategy ............................................................................................................ 27 

What to build first if time is genuinely limited .................................................................................................................. 28 

MVP vs. future scope — direct recommendation ............................................................................................................. 28 

Part R — Technology Decision Guide ................................................................................................................................... 28 

Part S — Developer Toolkit .................................................................................................................................................... 34 

Recommended installation order ........................................................................................................................................ 35 

Common beginner mistakes per tool, worth flagging early ............................................................................................. 35 

Closing Note ............................................................................................................................................................................. 48 

 
 
  

Page 3 of 48 



TrustNet AI — Engineering Blueprint 

How to Use This Document 

This document is the complete engineering blueprint for TrustNet AI, written as a single reference a new team member 
could build from without asking clarifying questions. It is organized into six parts: (A) the build lifecycle from research 
to deployment, (B) repository and service architecture, (C) the four cross-cutting engines (backend, database, Kafka, 
gateway, auth, explainability, trust score), (D) infrastructure and operations (deployment, monitoring, git, testing, risks, 
standards), (E) the AI research and dataset plan for every detection module, and (F) the technology decision guide and 
developer toolkit. 

Every recommendation in this document follows one rule, applied consistently: choose the option that a four-person 
student team can actually build, debug, and explain in a viva within two semesters, while keeping the architecture 
honest about what would need to change to serve real production traffic. Where the fastest option and the most correct 
option differ, that tradeoff is called out explicitly rather than hidden. 

 

Part A — Development Lifecycle (Phase 0 to Phase 8) 

Nine phases, each with a concrete exit criterion. A phase is not 'complete' because time has passed — it is complete 
when its exit criterion is demonstrably true. This is what prevents the classic student-project failure mode of every 
module being '80% done' at the same time in week 20. 

Phase 0 — Research & Requirement Freeze (Weeks 1-2) 

Goal: convert the proposal into a frozen, specific requirement set before any architecture decision is made. 

• Re-read every detection module's requirement and write one paragraph per module stating exactly what input it 
accepts, what output it produces, and what 'done' looks like for the panel demo. 

• Shortlist datasets per module (see Part E) and download samples to confirm they actually load, are labelled as 
documented, and are legally usable — dataset problems discovered in week 2 are a rescoping decision; 
discovered in week 20 they are a crisis. 

• Freeze the non-negotiable MVP scope in writing (see Part F, MVP table) and get guide sign-off on it, so scope 
disagreements later have a reference point. 

Exit criterion: a one-page frozen requirement doc, signed off by the guide, listing exact inputs/outputs per module and 
the MVP boundary. 

Phase 1 — Architecture & Contracts (Weeks 3-4) 

Goal: design every service boundary and API contract before a single microservice is scaffolded. Changing a database 
schema after three weeks of built code is expensive; changing it on a whiteboard is free. 

• Draw the service boundary diagram (Part C) and get every team member to agree on which service owns which 
data — this is the single most valuable hour in the whole project, because it prevents circular dependencies later. 

• Write OpenAPI-style request/response contracts for every inter-service call (even in prose form: 'Scan Service 
calls POST /detect/image with {file_url, scan_id}, expects {score, confidence, evidence[]} back'). This lets two 
team members build both sides of an integration in parallel without waiting on each other. 

• Design the database schema (Part D) and the Kafka topic list (Part E) on paper first. 

Exit criterion: a shared architecture document (this one) plus a contracts appendix that every team member has 
reviewed and can explain. 

Page 4 of 48 



TrustNet AI — Engineering Blueprint 

Phase 2 — Repository & Skeleton Scaffolding (Week 5) 

Goal: an empty but runnable skeleton — every service starts, talks to every other service with a stub response, and the 
whole stack comes up with one command. 

• Create the full folder tree (Part B) even for services with no real logic yet — a service that returns {"status": 
"stub"} but is wired into the gateway, Kafka, and Docker Compose is worth more at this stage than a fully-built 
model with no integration path. 

• Get docker-compose up bringing up all core infra (Postgres, MongoDB, Redis, Kafka) plus stub services, on 
every team member's machine, on day one of this phase — not week 10. 

Exit criterion: docker-compose up works on all four laptops and a request from the frontend reaches a stub AI service 
and comes back through the gateway. 

Phase 3 — Backend Core Services (Weeks 6-8) 

Goal: Auth, Gateway, Scan Management, and the database layer are real (not stubbed) and independently testable. 

• Build Authentication Service first (JWT issuance, RBAC, refresh tokens) — every other service depends on it for 
testing, so it blocks the least if built early and blocks the most if built late. 

• Build the API Gateway's routing, auth-check, and rate-limiting middleware. 

• Build Scan Management Service (create scan, track status, store results) since it's the central orchestrator every 
detection module reports back to. 

Exit criterion: a user can register, log in, and create a scan record that persists — with zero AI models involved yet. 

Phase 4 — AI Model Development (Weeks 6-14, parallel to Phase 3/5) 

Goal: each detection module reaches a validated baseline, then an improved model, independently of the other three. 
This phase runs in parallel with backend work — model training does not block API development if the contracts from 
Phase 1 are honored. 

• Follow the module build order in Part F exactly: Phishing and Scam Message first (lowest risk, fastest to real 
numbers), then Fake Review, then DeepScan image → audio → video, with OSINT and Trust Fusion last. 

• Every model, once trained, is wrapped behind the same inference interface (Part D, plugin architecture) before it 
is considered 'done' — a model that only runs in a notebook is not integration-ready. 

Exit criterion: every MVP model produces a prediction + confidence + evidence object matching the standardized 
explainability schema (Part C.6), evaluated with real precision/recall/F1/AUC numbers on a held-out test set. 

Phase 5 — Integration (Weeks 12-16) 

Goal: real services replace stubs one at a time, Kafka event flow is live end-to-end, and the Trust Score Engine fuses 
real module outputs. 

• Integrate one detection service at a time, in the same priority order as Phase 4 — never do a 'big bang' integration 
of all five modules simultaneously, since debugging five newly-connected services at once is close to 
undebuggable with a four-person team. 

• Build the Trust Score Engine's fusion logic against real (not synthetic) module outputs as soon as two modules 
are integrated, so fusion bugs surface early rather than in week 18. 

Exit criterion: a real upload flows through gateway → Kafka → at least three real detection services → Trust Score 
Engine → stored report, with no stubs remaining in that path. 

Page 5 of 48 



TrustNet AI — Engineering Blueprint 

Phase 6 — Testing & Hardening (Weeks 15-17) 

Goal: the system survives concurrent use, bad input, and a service crash without cascading failure. 

• Run the full test pyramid (Part I): unit tests per service, integration tests per Kafka flow, a handful of end-to-end 
scenarios, and a basic load test (see Part I for tool choice). 

• Deliberately kill one service mid-flow and confirm the system degrades gracefully (e.g., a failed deepfake service 
should not prevent the phishing result from still reaching the user). 

Exit criterion: the system's core demo path survives one service restart, one bad file upload, and 20 concurrent scan 
requests without crashing. 

Phase 7 — Deployment (Week 18) 

Goal: the system runs from a documented, repeatable deployment procedure — not 'it works on my machine.' 

• Containerize every service, write the Kubernetes manifests (or a well-documented Docker Compose production 
profile if Kubernetes proves too heavy for the timeline — see Part D honesty note), and wire CI/CD for at least 
build+test on every push. 

Exit criterion: a fresh machine can deploy the full stack from the git repository alone, following only the README. 

Phase 8 — Documentation, Demo Prep & Scaling Story (Weeks 19-20) 

Goal: the panel defense is prepared, not improvised. 

• Finalize the architecture diagrams, the numbers table (accuracy/precision/recall/F1/AUC per module), and a 
rehearsed answer for 'how would this scale to a million users' (Part K). 

Exit criterion: every team member can independently answer 'walk me through what happens when a user uploads a 
video' end to end. 

 

Part B — Repository & Folder Structure 

The repository is a monorepo: one git repository holding every service, the frontend, and infrastructure code. For a 
four-person team this is deliberately chosen over multiple repositories — it means one PR can change an API contract 
and its two consumers atomically, one CI run validates the whole system, and there's no version-skew problem between 
repos that a small team doesn't have the process maturity to manage yet. This is the single biggest simplification 
relative to a 'textbook' enterprise setup, and it is the right one for your team size. 

Folder Contains Owner May depend on 

React 19 + TS web app — dashboard, upload Whoever owns UI; all members 
frontend/ gateway/ (API contracts only) 

center, reports, auth UI read 

FastAPI API Gateway — routing, auth-check, 
gateway/ Backend lead services/* (via HTTP), shared/ 

rate limiting, request validation 

One subfolder per microservice (auth, scan, ai-
Split by owner, one service per 

services/ orchestration, trust-engine, notification, shared/, own DB only 
person where possible 

analytics, report, dataset) 

AI model code — isolated per modality, see shared/ for common 
models/ AI/ML-focused member(s) 

Part D for full breakdown preprocessing utils only 

Page 6 of 48 



TrustNet AI — Engineering Blueprint 

Folder Contains Owner May depend on 

Cross-service code: schemas, constants, Whole team, PR-reviewed 
Nothing — this is a leaf 

shared/ logging setup, common exceptions, auth-token strictly (breaking this breaks 
dependency 

verification helper everyone) 

Dockerfiles per service, docker-compose.yml 
docker/ DevOps-focused member n/a — infra definition 

(dev) and docker-compose.prod.yml 

Kubernetes manifests: deployments, services, 
k8s/ ingress, configmaps, secrets templates (no real DevOps-focused member docker/ (image references) 

secrets committed) 

Infrastructure-as-code if used (Terraform) — 
infra/ DevOps-focused member n/a 

optional for MVP, see Part D 

One-off dev scripts: seed database, generate shared/, services' repositories 
scripts/ Whole team, ad hoc 

test data, bulk model evaluation runner directly for seeding 

Prometheus config, Grafana dashboard JSON n/a — reads service /metrics 
monitoring/ DevOps-focused member 

exports, alert rules endpoints 

Cross-service integration/E2E tests that don't 
gateway/, services/* (as black 

tests/ belong inside a single service's own tests/ Whole team 
box, over HTTP) 

folder 

Environment-level config templates 
configs/ (.env.example per environment), NOT real DevOps-focused member n/a 

secrets 

This blueprint, API contracts, ADRs 
docs/ Whole team n/a 

(architecture decision records), runbooks 

 

Root-level files 

• README.md — single entry point: how to run the whole stack in under 10 minutes. 

• docker-compose.yml — brings up every service + infra for local development. 

• .env.example — every environment variable any service needs, with placeholder values and a one-line comment 
each. 

• Makefile or justfile — wraps the common commands (up, down, test, lint, seed) so nobody memorizes docker 
flags. 

Rule of thumb used throughout this document: a folder exists only if it answers 'why should this exist / what happens if it 
doesn't' with something more specific than 'convention.' Every folder above earns its place because removing it would 
force something into the wrong owner's hands or create a hidden cross-service dependency. 

 

Part C — Microservice Architecture 

How many services, and why 

Sixteen logical services are listed below. That is the correct count for the target architecture, but — stated plainly, 
because this is the single most important pragmatic call in this document — sixteen independently deployed, 
independently scaled microservices is not what four students should actually run in week 6. The recommendation is a 
two-stage approach: 

• Stage 1 (MVP, weeks 5-16): implement all sixteen as separate Python modules/packages with clean interfaces 
and their own Dockerfile, but deploy them as 3-4 process groups behind the same gateway (a 'modular monolith' 

Page 7 of 48 



TrustNet AI — Engineering Blueprint 

per group: e.g., all five detectors can run as one FastAPI app with five routers during development, since they 
share no state and only communicate via Kafka events in the target design anyway). 

• Stage 2 (post-MVP / scaling story for the panel): split each module into its own container and Kubernetes 
deployment — this is mechanical once the interfaces are clean, because Kafka-based communication doesn't care 
whether the consumer is in-process or a separate pod. 

This staging is not cutting a corner — it is the correct engineering call. A microservice boundary is a deployment/scaling 
boundary, not a code-organization boundary; you get the code-organization benefit (isolation, clear ownership, testability) 
from clean module boundaries whether or not each module has its own container from day one. Present both stages to the 
panel: it demonstrates you understand *why* microservices exist rather than cargo-culting the pattern. 

 

Service Directory 

Service Responsibility Reached via Owns DB Publishes Consumes 

Authentication Login, register, JWT PostgreSQL 
Gateway (sync) user.registered — 

Service issue/refresh, RBAC checks (users, roles) 

Scan Management Create scan, track lifecycle, Gateway (sync), all PostgreSQL 
scan.created detector.*.completed 

Service orchestrate fan-out detectors (async) (scans) 

Routes a scan's content to the 
AI Orchestration Scan Mgmt (async Redis (in-flight 

correct detector(s), tracks detection.requested scan.created 
Service via Kafka) state) 

completion 

URL feature extraction + 
Phishing Detection MongoDB 

BERT/GNN/LightGBM Kafka only detector.phishing.completed detection.requested 
Service (results) 

inference 

Scam Message Text classification MongoDB 
Kafka only detector.scam.completed detection.requested 

Detection Service (RoBERTa/DistilBERT) (results) 

Fake Review Review text + behavior analysis MongoDB 
Kafka only detector.review.completed detection.requested 

Detection Service (SBERT/XGBoost) (results) 

MongoDB 
Image Deepfake Image forensic + semantic 

Kafka only (results), S3 detector.image.completed detection.requested 
Service pipeline 

(media) 

Audio Deepfake MongoDB 
MFCC/Wav2Vec2 pipeline Kafka only detector.audio.completed detection.requested 

Service (results), S3 

Video Deepfake MongoDB 
Frame/temporal pipeline Kafka only detector.video.completed detection.requested 

Service (results), S3 

External verification, metadata MongoDB 
OSINT Service Kafka only detector.osint.completed detection.requested 

cross-check (results) 

Trust Engine CDCF fusion, weighted scoring, Kafka (consumes all PostgreSQL 
trust_score.generated detector.*.completed 

Service contradiction detection detector.*.completed) (trust scores) 

Explainability Aggregates per-module evidence Kafka, or called sync MongoDB 
explanation.generated trust_score.generated 

Service into one human-readable report by Report Service (explanations) 

Notification PostgreSQL 
Email / in-app alerts Kafka — trust_score.generated 

Service (notification log) 

PostgreSQL / 
Aggregated stats for the Kafka (consumes 

Analytics Service MongoDB read — all events 
dashboard everything, async) 

replicas 

Report Generation Sync, called by S3 (generated 
PDF/HTML report assembly report.generated — 

Service frontend via gateway reports) 

Manages training data, 
S3, PostgreSQL 

Dataset Service versioning (internal/admin use Sync, admin-only — — 
(metadata) 

only) 

 

Should Image, Audio, and Video be one service or three? 

Page 8 of 48 



TrustNet AI — Engineering Blueprint 

Three separate services, communicating only via Kafka events keyed by scan_id. Reasoning, compared directly: 

One combined 'DeepScan' service (rejected for production, acceptable for early MVP) 

• Advantage: fewer moving parts to wire up in week 6-8; one Dockerfile, one deployment. 

• Disadvantage: video inference is far more compute/GPU-hungry than image or audio — bundling them means 
you cannot scale (or afford GPU time for) the heavy one without paying the same cost for the light ones. It also 
means a crash or dependency conflict in the video pipeline (e.g., a specific OpenCV/ffmpeg version) takes down 
image and audio detection too. 

Three separate services (recommended target, and worth building this way once Phase 4 starts) 

• Advantage: independent scaling — you can run more replicas of whichever modality is the bottleneck; 
independent failure — a video pipeline crash never blocks image/audio results from reaching the user; 
independent dependency management — video's ffmpeg/OpenCV stack doesn't collide with image's torchvision 
or audio's librosa versions; matches the real datasets/training pipelines, which are already separate per modality. 

• Disadvantage: three services to deploy and monitor instead of one, more Kafka topics to manage, more 
integration surface area. 

Given the disadvantages are operational (more YAML, more dashboards) rather than architectural, and the advantages 
are architectural (failure isolation, independent scaling, dependency isolation), three separate services is the correct call 
even for a student project — implement them as three separate Python packages under models/ from day one (Part D), 
and worry about whether they're one container or three only at deployment time. 

 

Part D — AI Model Organization & Plugin Architecture 

Folder layout under models/ 

Every modality gets an identical internal skeleton. This uniformity is deliberate: once one team member has built the 
image pipeline, anyone else building audio or video already knows where everything lives. 

• models/<modality>/data/ — raw + processed dataset references (not the data itself, which lives in S3/local 
storage — this folder holds loader scripts and a manifest of what's where). 

• models/<modality>/preprocessing/ — cleaning, normalization, augmentation, feature extraction specific to that 
modality. 

• models/<modality>/training/ — training loop, hyperparameter config, the script that produces a checkpoint. 

• models/<modality>/experiments/ — one subfolder per training run, named by date+config hash, holding logs and 
metrics — this is what lets you answer 'which run produced the checkpoint we shipped' six weeks later. 

• models/<modality>/checkpoints/ — only the checkpoint(s) actually promoted to 'current best' (large binary files; 
do not commit to git — use .gitignore + a small manifest.json listing which experiment produced each one, with 
the binaries themselves in S3/local storage or Git LFS if truly necessary). 

• models/<modality>/inference/ — the thin, stable wrapper the rest of the system actually calls (see plugin 
interface below) — this is the only file other services are allowed to import from. 

• models/<modality>/evaluation/ — scripts that compute precision/recall/F1/AUC on a held-out test set, and the 
report each run produced. 

• models/<modality>/explainability/ — Grad-CAM/SHAP/attention-extraction code specific to that modality, 
called by inference/ to populate the evidence field. 

Page 9 of 48 



TrustNet AI — Engineering Blueprint 

• models/<modality>/configs/ — YAML/JSON config for that modality's model (hyperparameters, thresholds, 
paths) — never hardcoded in Python. 

 

Plugin architecture: build image first, add the rest without rewriting 

The mechanism that makes this possible is a single shared interface every detector implements, defined once in shared/ 
and never modified per-modality: 

• Every detector exposes exactly one function with a fixed signature: predict(input) → DetectionResult, where 
DetectionResult is a standard schema: {score: float 0-1, confidence: float 0-1, label: str, evidence: 
list[EvidenceItem], metadata: dict}. 

• The Scan Orchestration layer never imports a specific model class — it holds a registry (a dict mapping 
detector_type → its predict function) and looks up which one to call based on the content type of the current 
scan. Adding video means adding one entry to this registry, not touching orchestration logic. 

• Each detector's inference/ module is free to change its internals completely — swap EfficientNet for a different 
backbone, retrain with a new dataset — as long as predict() keeps the same input/output contract. This is what 
'replaceable without affecting the rest of the project' means concretely: the contract is the interface, not the 
implementation. 

• Kafka reinforces this naturally: a new detector just needs to consume detection.requested events filtered by its 
content type and publish its own detector.<name>.completed event — no other service's code changes when a 
new detector is added, only the Trust Engine's fusion weight config needs a new entry. 

Concretely for your build order: build the Image Deepfake predict() function and its DetectionResult output first, wire it 
fully through orchestration → Kafka → Trust Engine → frontend so the whole pipe works end-to-end for one modality. 
Every subsequent modality (audio, video, scam, phishing, review) is then 'implement predict() matching the same contract' 
— a repeatable, well-understood task instead of a fresh integration project each time. 

 

Part E — Backend Architecture (per-service FastAPI layout) 

Every service — Auth, Scan Management, each detector, Trust Engine — follows the same layered structure internally, 
for the same reason the models/ folder is uniform across modalities: once one service is understood, every other service 
is navigable without a walkthrough. 

Layer/Folder Purpose Notes 

FastAPI route declarations only — no logic, just wiring 
routers/ Everyone touches their own service's routers 

HTTP methods to controller functions 

Thin layer — if a controller function is more than 
Request/response handling: parse input, call the right service 

controllers/ ~15 lines, logic has leaked in that belongs in 
function, shape the response 

services/ 

Actual business logic — this is where 'create a scan', 'compute 
services/ The layer that gets unit-tested the most 

fusion score' etc. actually happens 

Database access only — every SQL/Mongo query lives here, Swapping Postgres for another store only touches 
repositories/ 

nowhere else this layer 

Pydantic request/response models — the API contract, 
schemas/ Shared with shared/ for cross-service schemas 

validated automatically by FastAPI 

ORM table definitions (SQLAlchemy) — distinct from AI 
models/ (db) One file per table/collection 

models/, deliberately named 'db_models' to avoid confusion 

Page 10 of 48 



TrustNet AI — Engineering Blueprint 

Layer/Folder Purpose Notes 

Internal data-transfer objects when a schema needs to look Used sparingly — only when schemas/ and 
dtos/ 

different between layers (e.g., DB row vs. API response) db_models/ genuinely need to diverge 

Custom validation logic beyond what Pydantic handles Called from controllers/ before the service layer 
validators/ 

declaratively (e.g., file-type/size checks, cross-field rules) runs 

Cross-cutting request handling: auth-token verification, 
middleware/ Runs on every request, applies to whole service 

request logging, error formatting 

App startup/wiring: FastAPI app instance creation, router 
core/ One file, rarely touched after week 6 

registration, startup/shutdown events 

Settings loaded from environment variables (pydantic- Never hardcode a value that could differ between 
config/ 

settings), one Settings class per service dev/prod here 

database/ Connection/session management, migration runner hookup Repositories depend on this, nothing else should 

Small, stateless helper functions with no service-specific logic If a function needs the DB or another service, it 
utils/ 

(date formatting, id generation) doesn't belong here 

Background task definitions (FastAPI BackgroundTasks or a 
Distinct from Kafka — used for in-process quick 

background/ lightweight queue) for fire-and-forget work like sending a 
tasks only 

notification 

Structured logger setup (JSON logs with request/trace id), 
logging/ Lives in shared/, imported not duplicated 

shared config imported by every service 

Only services that actually cache something need 
caching/ Redis client wrapper + cache-key conventions for that service 

this folder 

 

Request flow through the layers (within one service) 

router → middleware (auth check, logging) → controller (parse/validate) → service (business logic) → repository (DB) 
→ back up through the same chain to the response. Dependency Injection (FastAPI's built-in Depends()) is used to 
hand each layer only what it needs — a controller receives a service instance via Depends(), a service receives a 
repository via Depends() — so any layer can be unit-tested by injecting a fake/mock of the layer below it, without 
spinning up a real database. 

Discipline that matters more than the folder names: a repository function is the only place a raw SQL/Mongo query is 
allowed to appear anywhere in the codebase. If you find a query string inside a controller during code review, that's the 
one architectural rule worth being strict about — it's what keeps a future database migration a one-folder change instead 
of a codebase-wide hunt. 

 

Part F — Database Design 

What goes where, and why 

Three data stores, each earning its place by a genuinely different access pattern — not 'because the proposal said so.' 
PostgreSQL holds anything that is relational, needs strong consistency, and is queried with joins/filters (users, scans, 
trust scores, audit-critical records). MongoDB holds anything whose shape varies per record and is written far more 
than it's transactionally updated (raw AI outputs, explanations, OSINT results, logs). Redis holds anything that is short-
lived, high-read-frequency, and can be safely lost (sessions, rate-limit counters, hot-scan cache). 

PostgreSQL — relational core 

Page 11 of 48 



TrustNet AI — Engineering Blueprint 

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

Relationships: users 1—N scans (a user has many scans); scans 1—1 trust_scores (one fused score per scan); scans 1—
N reports (a scan can be re-exported as a report multiple times); users 1—N notifications. Foreign keys enforced at the 
DB level for these — they are genuinely relational and benefit from Postgres's constraint checking. 

MongoDB — flexible, high-volume documents 

Collection Shape Why Mongo, not Postgres 

One document per detector per scan: {scan_id, Schema varies per detector — 
detection_results detector_type, score, confidence, evidence:[...], Mongo's flexibility is exactly why 

raw_model_output, created_at} this doesn't belong in Postgres. 

Large, nested, read-heavy 
{scan_id, natural_language_summary, 

explanations documents assembled from 
per_modality_evidence:[...], heatmap_refs:[...]} 

detection_results. 

Never needs joins; write-heavy — 
audit_logs / detection_logs High-volume append-only event records 

wrong fit for a relational table. 

Loosely structured external-verification results (varies No fixed schema across sources — 
osint_metadata 

wildly by source) Mongo again the right fit. 

Redis — ephemeral, hot-path data 

• Session tokens / refresh-token blocklist (short TTL, checked on every authenticated request — must be fast). 

• Rate-limit counters per user/IP (incremented on every gateway request — needs to be near-instant). 

• Frequently-scanned URL cache — if the same URL is submitted twice, skip re-running the full phishing pipeline 
and serve the cached score (with a sensible TTL, since a domain's reputation can change). 

• In-flight scan orchestration state — 'which of the 4 requested detectors have reported back for scan X' — 
read/written constantly during a scan's lifecycle, discarded once the scan completes and its result is persisted to 
Postgres/Mongo. 

What should never be stored in any of these 

• Raw uploaded media files — these belong in S3/MinIO object storage; the databases store only a reference 
URL/key, never the binary itself. 

• Plaintext passwords or raw JWT secrets — hashed passwords only (bcrypt/argon2), and secrets belong in a secret 
manager / environment variables, never in any database table. 

• Large model checkpoints or training datasets — these belong in object storage or a model registry, not in an 
operational database. 

Scaling notes 

• Postgres: read replicas for the Analytics Service (it should never query the primary that Auth/Scan write to); 
partition scans/trust_scores by created_at if volume grows large — not needed for an academic project's demo 
scale, but worth naming in the panel's 'how would this scale' discussion. 

Page 12 of 48 



TrustNet AI — Engineering Blueprint 

• Mongo: shard detection_results by scan_id hash at production scale; for the project, a single instance with proper 
indexes on scan_id is entirely sufficient. 

• Redis: this is inherently horizontally scalable (Redis Cluster) and is the cheapest piece of this stack to scale later, 
so it's reasonable to run a single instance for the whole project lifetime. 

 

Part G — Kafka Event Architecture 

When to use Kafka, and when not to 

Use Kafka for anything that is fire-and-forget from the producer's perspective, can tolerate being processed a few 
seconds later, and has more than one interested consumer, or where the producer must not block waiting on a slow 
downstream step (AI inference). That is exactly the shape of 'a scan was created, now four independent, slow AI 
services need to process it and one aggregator needs to hear from all of them.' 

• Use Kafka for: scan creation fan-out to detectors, detector-completion events feeding the Trust Engine, trust-
score-generated events feeding notification/analytics/reporting — anything async, multi-consumer, or latency-
tolerant. 

• Do NOT use Kafka for: user login (needs an immediate response — this is a synchronous HTTP call to Auth 
Service), fetching a user's scan history for the dashboard (a direct, synchronous read from the database via the 
Gateway → Scan Mgmt call), or any request where the user is actively waiting on screen for an answer within a 
second or two. Kafka is for decoupled background work, not for the request/response backbone of the app. 

Topic list 

Topic Producer Consumer(s) Why this event exists 

A new scan needs to be routed to 
scan.created Scan Mgmt AI Orchestration 

detectors 

One topic per content type keeps 
Corresponding detector 

detection.requested.<type> AI Orchestration unrelated detectors from consuming 
service only 

irrelevant events 

Trust Engine, Scan Mgmt Detector finished; carries its 
detector.<name>.completed Each detector service 

(status tracking) DetectionResult payload 

Notification, Explainability, Fusion complete; downstream 
trust_score.generated Trust Engine 

Analytics consumers fan out 

Report Service (on demand), Human-readable report content is 
explanation.generated Explainability Service 

Analytics ready 

Reliability mechanics 

• Retries: each consumer wraps its processing in a retry policy (e.g., 3 attempts with exponential backoff) for 
transient failures (a model server briefly unavailable) — this is consumer-side, not a Kafka feature per se. 

• Dead Letter Queue: after retries are exhausted, the message is published to a corresponding <topic>.dlq topic 
instead of being dropped silently — a monitoring alert fires when the DLQ receives anything, and someone 
investigates rather than a scan silently vanishing. 

• Idempotency: every event carries a stable scan_id + detector_type key; consumers check 'have I already written a 
result for this key' before processing, so a redelivered message (which Kafka's at-least-once delivery guarantees 
can produce) never double-counts or double-notifies. 

Page 13 of 48 



TrustNet AI — Engineering Blueprint 

• Event versioning: every event payload includes a schema_version field from day one, even though it will be '1' 
for the whole project — this costs nothing now and is the difference between a clean and a painful schema 
change later, which is exactly the kind of decision this document asks you to make with a one-year lens even on a 
project with a 20-week horizon. 

Practical scope note: for the actual student build, a lighter-weight broker (RabbitMQ, which your own proposal draft lists 
as an alternative) is a reasonable substitute if Kafka's operational overhead (Zookeeper/KRaft, partition management) 
eats into your timeline — the event-driven pattern described above is identical either way, only the broker changes. Kafka 
is the right choice to present in the architecture diagram as the production target; RabbitMQ is a legitimate, faster-to-
operate substitute for the actual weeks-6-through-16 build if your team hasn't run Kafka before. 

 

Part H — API Gateway, Request Flow & Authentication 

Request flow, step by step 

• 1. User → Gateway: request hits FastAPI Gateway over HTTPS (TLS terminated at NGINX in front of it). 

• 2. Authentication: Gateway middleware extracts the JWT from the Authorization header, verifies its signature 
and expiry against Auth Service's public key (or a shared secret for a symmetric-signing MVP) — this is a local, 
fast check, not a network call to Auth Service on every request. 

• 3. Authorization (RBAC): the decoded token's role claim is checked against the route's required permission (e.g., 
only 'admin' or 'moderator' can access the Dataset Service's admin endpoints) — a request that fails this returns 
403 before touching any service. 

• 4. Validation: the request body is validated against the route's Pydantic schema — malformed input is rejected 
with 422 before any business logic runs. 

• 5. Routing to microservice: the Gateway forwards the validated request to the appropriate internal service over 
HTTP (for synchronous calls like 'create a scan') or publishes a Kafka event (for the async detection fan-out that 
scan creation triggers). 

• 6. Kafka: for anything async, the receiving service (e.g., Scan Mgmt) publishes to Kafka, detector services 
consume, process, and publish their own completion events — the Gateway is not involved in this internal fan-
out at all. 

• 7. Database: each service reads/writes only its own owned tables/collections (Part F) — no service reaches into 
another service's database directly. 

• 8. Response: for synchronous calls, the result flows back up through the same chain to the Gateway and out to the 
user. For async flows, the initial response is 'scan created, poll or subscribe for status' — the user does not wait 
on screen for AI inference to complete. 

Authentication design 

• Access token: short-lived JWT (e.g., 15 minutes), carries user_id and role, verified locally by every 
service/gateway without a database round-trip. 

• Refresh token: longer-lived (e.g., 7 days), stored server-side (Redis) so it can be revoked, used only to mint new 
access tokens via a dedicated Auth Service endpoint. 

• Roles: Admin (full platform access, dataset management), Moderator/Researcher (view all scans, override flags, 
no user management), User (own scans only), Guest (rate-limited, unauthenticated demo access if offered). 

• Folder structure inside Auth Service: routers/ (login, register, refresh, logout), services/ (token issuance, password 
hashing), repositories/ (users, roles tables), middleware/ (the token-verification function that shared/ exposes for 

Page 14 of 48 



TrustNet AI — Engineering Blueprint 

every other service to reuse — write this once, import everywhere, never reimplement JWT verification per 
service). 

The one rule worth being strict about: JWT verification logic exists in exactly one place in the codebase 
(shared/auth/verify.py or equivalent), imported by every service's middleware. Copy-pasting token verification into five 
services is a guaranteed source of a security bug when one copy gets updated and four don't. 

 

Part I — Explainable AI & Trust Score Engine 

Standardized explainability output 

Every detector, regardless of modality, returns the same explainability shape — this is what lets the Explainability 
Service assemble a coherent report without modality-specific glue code: 

• prediction — the label (e.g., 'phishing', 'legitimate', 'likely deepfake'). 

• confidence — the model's own calibrated confidence in that prediction, 0-1. 

• evidence — a list of {feature_or_region, contribution, human_readable_note} items: for image, a Grad-CAM 
region + its SHAP-style contribution; for text (scam/phishing/review), the specific tokens/phrases that drove the 
decision; for audio, the MFCC coefficients or time segments that were most influential. 

• metadata — raw supporting facts (domain age for phishing, sentence length for scam text, frame count analyzed 
for video) that a human reviewer might want without needing model internals. 

• heatmap_ref (optional) — a stored reference to a visual overlay (Grad-CAM image, waveform highlight) for 
modalities where that applies. 

The Explainability Service's job is purely aggregation and natural-language templating: it takes the evidence lists from 
every detector that ran on a scan, plus the fused trust score, and produces one paragraph a non-technical user can read 
— this is a templating/summarization task, not a new model, which keeps it tractable for a four-person team. 

 

Trust Score Engine — fusion architecture 

Input: the set of per-module scores that actually ran for a given scan (not every scan triggers every module — a plain-
text scam-message scan never produces an image score, for instance, so the fusion logic must handle a variable-length 
input set). 

• Step 1 — Normalization: every module's raw output is mapped onto the same 0-100 scale before fusion, since 
'phishing probability' and 'deepfake authenticity score' are not naturally on the same numeric footing. 

• Step 2 — Weighted combination: a validation-set-derived weight per module (following BGL-PhishNet's 
precedent of cross-validated weighting, discussed earlier in this project's literature review) combines the 
normalized scores. Start simple: a weighted average is a legitimate, defensible, implementable v1 — do not over-
engineer this into a learned meta-model until the simple version is working and measured. 

• Step 3 — Contradiction detection: a rule layer checks for cases where modules disagree sharply (e.g., image 
score says 'authentic' but OSINT says 'this exact image was flagged as manipulated elsewhere') and applies a 
penalty or flags the case for lower-confidence output rather than silently averaging away a real disagreement — 
this is the single most novel piece of the whole system relative to the reference literature reviewed earlier, and it 
deserves to be simple and explainable rather than a black box. 

• Step 4 — Risk-level mapping: the final 0-100 score maps to Low/Medium/High/Critical via fixed, documented 
thresholds (not learned) — this keeps the mapping auditable and explainable in a viva. 

Page 15 of 48 



TrustNet AI — Engineering Blueprint 

Build order for this engine specifically: implement Steps 1 and 2 first against two real modules (phishing + scam), get that 
working and tested, then add Step 3's contradiction logic once three or more modules are live. Do not attempt 
contradiction detection against only one or two modules — there's nothing to contradict yet. 

 

Part J — Deployment Architecture 

Docker 

Concern Guidance 

python:3.11-slim per service; a separate CUDA-enabled base only for GPU-dependent 
Base image inference services (video/image deepfake) — do not put CUDA in every image, it bloats 

build time and image size for services that never touch a GPU 

Separate the dependency-install stage from the runtime stage so build tools don't bloat the 
Multi-stage builds 

final image 

.dockerignore Exclude checkpoints/, experiments/, tests/, .git — keep images lean 

Every service exposes /health (liveness — is the process up) and /ready (readiness — can it 
Health checks 

actually serve, e.g. DB connection established) 

Docker Compose vs. Kubernetes — honest guidance 

Docker Compose is the correct tool for local development and is a legitimate production deployment target for a project 
at this scale and this team size. Kubernetes is the correct target architecture to design for and present in diagrams, but 
running a real K8s cluster (even a lightweight one like k3s/minikube) adds genuine operational overhead — ingress 
config, secret management via K8s Secrets, persistent volume claims for stateful services — that competes directly 
with time spent getting AI modules working. 

• Recommended real path: build and demo on Docker Compose (a docker-compose.prod.yml profile with proper 
resource limits, restart policies, and health checks is a completely legitimate 'deployment architecture' for a panel 
defense) — and have the Kubernetes manifests written and explained (even if only tested on a local k3s cluster 
once, not run continuously) as the documented scaling path. This is honest engineering communication: 'here is 
what we run, here is what we've designed and validated as the path to more scale' is a stronger answer than a half-
working K8s cluster on demo day. 

Kubernetes concepts to have ready regardless 

• Ingress — single entry point routing external traffic to the Gateway service, TLS termination. 

• ConfigMaps — non-secret configuration (feature flags, thresholds) injected as environment variables. 

• Secrets — DB credentials, JWT signing keys, API keys for OSINT sources — never committed to git, injected at 
deploy time. 

• Volumes — persistent storage claims for stateful components (Postgres, MongoDB) if not using 
managed/external instances. 

• Liveness/Readiness probes — map directly to each service's /health and /ready endpoints. 

• Horizontal Pod Autoscaling — the concrete answer to 'how would this scale to a million users': scale detector 
pods independently based on Kafka consumer lag or CPU, which is exactly why the three-separate-deepfake-
services decision in Part C pays off here. 

 

Page 16 of 48 



TrustNet AI — Engineering Blueprint 

Part K — Monitoring & Observability 

• Prometheus scrapes a /metrics endpoint on every service (request count, latency histograms, error rate, and for AI 
services, inference-time and queue-depth) — instrument this from week 6, not week 18, since retrofitting metrics 
into finished services is far more work than adding them as each service is built. 

• Grafana dashboards, minimum viable set: one system-health overview (request rates/errors across all services), 
one AI-pipeline dashboard (per-detector latency and throughput), one Kafka dashboard (consumer lag per topic 
— this is your earliest warning sign of a bottleneck). 

• ELK (or a lighter Loki+Grafana stack, which is less operationally heavy for a student team and worth considering 
as a substitute) for centralized logs — every service logs structured JSON with a request/trace id so a single user-
reported issue can be traced across every service it touched. 

• Alerts, minimum set worth configuring: Kafka DLQ receiving any message, any service's error rate exceeding a 
threshold, any service failing its readiness probe for more than a minute. 

Same honesty principle as Kubernetes: a working Prometheus + Grafana setup with three real dashboards is more 
valuable, and more defensible in a viva, than a fully-configured ELK stack that was set up once and never actually used to 
debug anything. Build the observability you will actually look at. 

 

Part L — Git Strategy & Team Workflow (4 members) 

Branch Purpose Protection rule 

main Always deployable; only merges from release/* Protected: PR + passing CI + 1 review required 

Integration branch; where feature branches merge 
develop Protected: PR + passing CI required 

first 

One per unit of work (e.g., feature/phishing-
feature/<name> Branched from develop, merged back via PR 

inference-api) 

hotfix/<name> Urgent fix branched directly from main Merged to both main and develop 

release/<version> Stabilization before a milestone/demo Merged to main and tagged 

• Pull Requests: every feature branch opens a PR into develop; PR description must state which service(s) it 
touches and whether it changes any API contract (contract changes get flagged for a second reviewer regardless 
of team member load). 

• Code review: minimum one reviewer, and it should not always be the same person — rotate so every team 
member develops a working understanding of every service, which matters directly for the panel defense's 'can 
everyone explain the whole system' bar. 

• Merge policy: squash-merge feature branches into develop to keep history readable; merge develop into release/* 
only when Phase exit criteria (Part A) are met, not on a fixed calendar date. 

 

Part M — Testing Strategy 

• Unit tests (tests/ inside each service) — service-layer business logic and repository-layer query correctness, run 
on every PR via CI. 

• Model tests (models/<modality>/evaluation/) — precision/recall/F1/AUC on a held-out set, re-run whenever a 
checkpoint changes, results logged to experiments/ so regressions are visible. 

Page 17 of 48 



TrustNet AI — Engineering Blueprint 

• Integration tests (root tests/) — Kafka producer→consumer flows using a test broker (or testcontainers), e.g. 
'publishing scan.created results in the right detector.requested events.' 

• API tests — contract-level tests against the Gateway (can reuse the OpenAPI schema generated by FastAPI to 
catch drift automatically). 

• End-to-end tests — a small number (5-10) of full-path scenarios: upload image → expect a trust score within N 
seconds; these are the tests that most directly validate the Phase 6 exit criterion. 

• Load tests — a lightweight tool (Locust or k6, both free and simple to script) simulating concurrent scan 
submissions, watching Kafka consumer lag and API latency under load. 

• Security tests — basic checks: can an unauthenticated request reach a protected route, does file upload reject 
disallowed types/oversized files, is SQL injection possible through any raw-input field (it shouldn't be, given the 
repository-only-queries rule). 

 

Part N — Risk Register 

Risk Why it happens How to prevent it 

Enforce: services communicate only over HTTP or 
Tight coupling between Services calling each other's internal 

Kafka, never by importing another service's code — 
services functions directly instead of via API/Kafka 

a linter/CI check can catch cross-service imports 

Resolve at Phase 1 (contracts) by assigning clear 
Two services each needing data the other single ownership per data type; if it recurs, it's a sign 

Circular dependencies 
owns the service boundary is drawn wrong, not a code 

problem to patch around 

Model replacement A detector's inference code tightly coupled The predict() interface contract (Part D) exists 
difficulty to orchestration logic specifically to prevent this 

Only GPU-dependent services use a CUDA base 
Huge Docker images / CUDA + all ML libraries in every service's 

image; multi-stage builds; shared base image layers 
slow builds image 

cached 

Anything AI-inference-related is async via Kafka; 
Slow API responses Synchronous calls waiting on AI inference the user gets an immediate 'scan created' response, 

not a blocking wait 

Orchestration tracks expected-vs-received detector 
Trust Engine reads partial results before all count per scan in Redis; fusion only triggers once 

Race conditions in fusion 
expected detectors have reported complete (or a timeout fires and fusion proceeds 

with what's available, clearly flagged as partial) 

Consumer group monitoring (lag alerts), DLQ for 
A crashed consumer stops processing, 

Kafka consumer failures poison messages, health-checked consumer 
events pile up unnoticed 

processes that auto-restart 

Sensible TTLs on all cached values; never cache 
Redis-cached phishing score becomes stale 

Cache inconsistency anything for longer than the underlying signal 
as domain reputation changes 

realistically stays valid 

Migrations are additive-first (new nullable columns 
Database migration Schema changes breaking a service mid- before removing old ones), run as a separate CI/CD 
problems deploy step before new code deploys, tested against a copy 

of real data shape 

Strict Pydantic validation everywhere, malware 
Unvalidated file uploads, injection via scanning on upload, parameterized queries only 

Security vulnerabilities 
unsanitized input (repositories layer enforces this), dependency 

vulnerability scanning in CI 

Page 18 of 48 



TrustNet AI — Engineering Blueprint 

Risk Why it happens How to prevent it 

shared/ code kept minimal and stable; each service 
Version conflicts across Two services pinning incompatible 

has its own requirements.txt/pyproject.toml, not one 
services versions of a shared library 

giant shared dependency file 

Explicit teardown after each inference call, memory 
Memory leaks in long- Model or tensor objects not released 

profiling during load testing (Phase 6), especially for 
running AI services between inference calls 

the video pipeline 

CPU-fallback mode for local dev (smaller/quantized 
models or mocked inference), GPU only required in 

GPU dependency / Development machines without GPUs 
the actual training/deployment environment (e.g., 

availability cannot run real inference locally 
Colab/Kaggle for training, a single shared GPU box 
or cloud instance for deployed inference) 

 

Part O — Coding Standards 

• Naming: snake_case for Python files/functions/variables, PascalCase for classes, kebab-case for Kafka topics and 
Docker service names, SCREAMING_SNAKE_CASE for constants and environment variables. 

• Folder conventions: every service mirrors the exact layer names from Part E — a new developer navigating any 
service already knows where to look. 

• Environment variables: every service reads config exclusively through a Settings class (pydantic-settings) — no 
os.environ.get() scattered through business logic; .env.example in the repo root lists every variable any service 
needs with a placeholder value and one-line comment. 

• Constants: magic numbers/strings (thresholds, risk-level cutoffs, Kafka topic names) live in a single constants 
module per service, imported everywhere, never hardcoded inline. 

• Shared libraries: kept deliberately minimal — schemas, the auth-verification function, the logging setup, and the 
DetectionResult contract. Anything more is a sign a shared library is becoming a dumping ground; resist the urge. 

• Versioning: semantic versioning (major.minor.patch) for the API contract exposed by the Gateway; every 
breaking schema change bumps the major version and both old and new versions are supported briefly during 
rollout. 

• Error handling: every service raises typed, custom exceptions (not bare Exception) caught by a single middleware 
layer that converts them into a standardized JSON error response — {error_code, message, request_id} — 
consistent across every service. 

• Logging: structured JSON logs everywhere, every log line carries a request_id/trace_id that's generated at the 
Gateway and threaded through every downstream Kafka event and service call, so one user complaint can be 
traced end to end. 

• API responses: a single standard envelope — {data, error, meta} — used by every endpoint in every service, so 
frontend code never has to special-case response shape per service. 

 

Part P — Development Order & Week-by-Week Roadmap 

Direct answer to 'what first — auth, image model, gateway, or frontend': Authentication Service first, because 
everything else needs it to be testable, and it is small and well-understood (low risk, unblocks everyone). Image 
deepfake model development starts in parallel almost immediately after, since it's the longest lead-time item (data + 
training + evaluation) and should not wait on backend completion. 

• Weeks 1-2 — Phase 0: requirement freeze, dataset shortlisting, MVP scope sign-off. 

Page 19 of 48 



TrustNet AI — Engineering Blueprint 

• Weeks 3-4 — Phase 1: architecture, API contracts, database schema, Kafka topic list, all on paper/docs, reviewed 
by the whole team. 

• Week 5 — Phase 2: repo skeleton, docker-compose up working with stub services on every machine. 

• Weeks 6-8 — Phase 3 backend core (Auth → Gateway → Scan Mgmt) running in parallel with Phase 4 starting 
on Phishing + Scam Message models (lowest-risk, fastest to real numbers) and Image deepfake 
data/preprocessing work beginning. 

• Weeks 9-11 — Phishing and Scam Message models reach evaluated baselines; Fake Review model work begins; 
Image deepfake model training begins; first real (non-stub) service integration (Phishing) into the Kafka pipeline. 

• Weeks 12-14 — Audio and Video deepfake work begins (image should be evaluated and integrating by now); 
Trust Score Engine v1 (Steps 1-2, weighted average) built against Phishing + Scam Message real outputs. 

• Weeks 15-16 — Remaining detectors integrate one at a time; OSINT module (scoped down per Part K of the 
earlier literature discussion) built last, since it has the least precedent and highest external-dependency risk; Trust 
Engine's contradiction-detection step added once 3+ modules are live. 

• Weeks 15-17 — Phase 6 testing and hardening runs alongside late integration. 

• Week 18 — Phase 7 deployment (Docker Compose production profile; Kubernetes manifests written and 
validated once). 

• Weeks 19-20 — Phase 8 documentation, numbers table finalized, panel defense rehearsal. 

 

Part Q — Designing for Future Channels (Telegram, WhatsApp, Email, 
Browser Extension, Mobile, Enterprise API) 

The reason today's architecture requires minimal change for these is that every future channel is, structurally, just a new 
client of the same Gateway API — none of them touch a detection engine, the Trust Score Engine, or the database layer 
directly. 

• Telegram/WhatsApp/Email scanners are thin adapter services: they receive a message/forwarded content from 
their respective platform's API/webhook, extract the URL/text/media, and call the exact same POST /scan 
endpoint on the Gateway that the web frontend calls today — no detector or fusion logic is touched. 

• Browser extension / Chrome plugin: calls the same Gateway API from the browser context instead of the React 
app; needs the Gateway to support CORS/extension origins and possibly a lighter-weight, faster 'quick check' 
endpoint for real-time browsing, which is an additive Gateway route, not an architecture change. 

• Mobile app: same API, different client — this is exactly why a clean API Gateway with a versioned, well-
documented contract (Part O) pays off; the mobile team never needs to know or care that detection happens via 
Kafka internally. 

• Enterprise/REST API for third parties: mostly a matter of adding API-key-based authentication as an alternative 
to JWT at the Gateway layer, plus rate-limit tiers — additive to the auth middleware, not a redesign. 

The concrete design decision that pays for all of this later: keep every channel-specific concern (Telegram bot logic, 
browser-extension UI, email parsing) entirely outside the Gateway/services/models boundary, in their own thin adapter 
codebases that only ever call the public Gateway API. If a future adapter ever needs to import internal service code 
directly to work, that's the signal the API contract is incomplete — fix the contract, not the rule. 

 

Part E-1 — Datasets Per Module 

Page 20 of 48 



TrustNet AI — Engineering Blueprint 

Every table below follows the same format and ends with a clear pick. The overall pattern across all five modules: start 
with the smallest, cleanest, most standard dataset to get a working baseline fast, then move to the largest well-known 
benchmark once the pipeline works, and reserve the hardest/most gated dataset for a generalization test rather than 
primary training — this order minimizes wasted setup time against gated/registration-required datasets before you even 
know your pipeline runs. 

1. Phishing / Malicious URL Detection 

Academic-
Dataset Source License Size Label quality Class 

imbalance dict 
project fit Ver

Good — 
BEST — matches 

Free, open, community- 40/60 Yes — this is 
PhishTank + Kaggle your literature base 

Kaggle / CC/Kaggle terms verified phishing/legit, the exact 
'Phishing Website ~549,000 URLs paper directly, 

PhishTank feeds — academic use phishing, manageable with dataset BGL-
URLs' (549K) large, clean, ready 

unrestricted Tranco/Alexa- resampling PhishNet used 
o use 

style legitimate t

Good, but 
~11,000 features are pre- Good as a fast 

Free, open, 
UCI Phishing UCI ML instances, 30 extracted (less Roughly Yes, for a baseline before 

c-
Websites Dataset Repository academi

re-extracted flexible for a balanced quick baseline moving to the raw-
friendly p

features BERT/GNN URL Kaggle set 
pipeline) 

Phishing-only; Good supplement 
Free, registration High — actively needs a separate Yes, for for a 'live detection' 

PhishTank live feed Streaming, 
hishtank.org required, rate- d by legitimate-URL freshness / a demo, not a 

(API) p
thousands/month verifie

limited community source (e.g., live demo primary training set 
Tranco top sites) alone 

Good, heavily 
Mendeley 'Web Page Reasonable 

~11,000 rows, feature-
Phishing Detection' Mendeley Data Free, CC BY Balanced Yes alternative to UCI 

87 features engineered 
dataset f UCI feels stale 

already i

2. Scam Message Detection 

Academic-
Dataset Source License Size Label quality Class imbalance erdict 

project fit V

13% spam / 87% 
Yes — the BEST for a fast, 

UCI ML Free, CC, Good, hand- ham — real 
SMS Spam Collection 5,574 SMS standard clean baseline — 

Repository / academic- labelled imbalance, needs 
(UCI) essages baseline dataset small enough to 

Kaggle mirror friendly m
spam/ham oversampling/class 

or this task iterate quickly 
weights f

Moderate — Good supplement 
Fraudulent E-mail Scam-heavy; 

scam-only, once SMS Spam 
Corpus (Kaggle Free, Kaggle ~4,000+ scam needs Enron or Yes, as a 

Kaggle needs a Collection baseline 
'Nigerian Prince' / 419 terms emails similar for the supplement 

legitimate-email works, to generalize 
scam emails) legitimate class 

source paired in beyond SMS 

N/A (this is the 
Use only as the 

Enron Email Dataset High — real 'legitimate' half of Yes, paired 
CMU / Kaggle Free for research ~500,000 legitimate-class 

(legitimate class corporate email, a pairing, not with a scam 
mirror use emails complement, not 

source) well-studied scam-labelled corpus 
standalone 

itself) 

Varies — check Varies, Variable — Only if SMS Spam 
Kaggle 'Scam/Fraud each dataset's typically verify labelling Collection + email 

Kaggle (varies by 
Call Transcripts' license small methodology Usually scam-only Case-by-case corpora prove 

uploader) 
community sets individually (hundreds-low per dataset insufficient for your 

before use thousands) before trusting it text style 

3. Fake Review Detection 

Page 21 of 48 



TrustNet AI — Engineering Blueprint 

Dataset Source License Size Academic-
Label quality Class 

imbalance project fit Verdict 

~7M reviews, 
Free for Good — Yelp's BEST — largest, 

some releases Fake reviews are Yes, widely 
Yelp Open Dataset academic/research own filter is a de most credible, 

Yelp (official include a a small minority used in 
(filtered/unfiltered use — read Yelp's facto weak label; closest to what your 

filtered — significant academic fake-
review split) open dataset) 

dataset terms of not a perfect 
use (suspected-

ground truth imbalance review research module description 
already lists 

fake) subset 

No native fake-
review label — 
you'd need to 
construct labels 

Good for scale and 
via heuristics Yes, if you're 

Amazon Reviews UCSD McAuley Free for academic Millions of realism, but higher 
(duplicate N/A without willing to do 

(2018/2023 release, Lab (Julian use, cite the reviews across setup cost than 
label 

McAuley Lab, UCSD) McAuley) dataset paper categories detection, burst derived labelling 
patterns) or use a engineering Yelp's pre-filtered 

subset 
subset with 
known labels 
from other 
papers 

Good as a clean 
1,600 hotel High — 

baseline before 
reviews (800 carefully 

Cornell NLP moving to noisier 
Ott et al. Deceptive truthful, 800 constructed, Perfectly Yes, excellent 

group (via Free, academic real-world Yelp 
Opinion Spam Corpus deceptive, via gold-standard 
(Cornell) ACL/associated use, widely cited balanced by for a controlled 

design baseline data — small size is 
site) MTurk- for early fake-

a real limitation for 
generated review NLP 
fakes) research a deep model 

though 

Good, purpose-
built and 
balanced, but 
'fake' class is Good practical 

~40,000 
machine- middle ground: 

reviews, 
Free, Kaggle generated text balanced, sizeable, 

Kaggle 'Fake Reviews Kaggle (research- roughly 
terms — check specifically, not Balanced by Yes, good ready-to-use — pair 

Dataset' (Amazon + derived, based on balanced 
construction starting point with Ott et al. for 

Yelp combined, ~40K) necessarily 
Salminen et al.) the original 

paper's license too real/fake (fake 
representative of validation on a 

generated via 
different fake-

GPT-2) all real-world 
fake review review style 
styles (paid 
human fakes, bot 
networks) 

4. Deepfake Detection — Image 

Dataset Source License Size Label quality Class 
imbalance Academic-project fit Verdict 

BEST for image-
~1.8M frame-level 

Free for High — one of Manageable — 
TU Munich frames from deepfake 

academic/research the most balanced Yes — the standard 
FaceForensics++ (official 1,000 classification — 
(FF++) use, requires established across academic image/frame 

research page, original + most model 
deepfake manipulation deepfake benchmark 

request access) signing a usage 
agreement manipulated 

videos benchmarks methods comparisons in 
the literature use 
this 

Good SECOND 
dataset — train 
on FF++, 
evaluate on 

High — designed Fake-heavy at 
Celeb-DF to 

Official project Free for research ~590 real + specifically to be video level but Yes, excellent as a 
demonstrate 

Celeb-DF (v2) page (request use, request ~5,600 fake harder/more frame generalization/robustness 
cross-dataset 

access) required videos realistic than extraction can test set 
FF++ rebalance generalization, a 

known weak 
point flagged in 
the literature 
review 

140k Real and Fake Good, but this is Good as a fast 
140,000 

Faces (Kaggle, GAN-generated- Perfectly Yes, for a quick, easy-to- Week-1 baseline 
Kaggle Free, Kaggle 

images, 
based on StyleGAN terms balanced start baseline to get the pipeline 

balanced face detection, 
+ Flickr faces) not face- working end-to-

Page 22 of 48 



TrustNet AI — Engineering Blueprint 

Dataset Source License Size Label quality Class 
imbalance Academic-project fit Verdict 

swap/reenactment end before 
deepfake moving to FF++'s 
detection heavier, access-
specifically — gated data 
different task, 
worth knowing 
the distinction 

High, but Use only if 
~100,000+ extremely large training infra can 

Official DFDC Free for research Real/fake split 
DFDC (DeepFake videos, — realistically handle its scale; 

page (Kaggle- use, check current documented, Only if compute budget 
Detection Challenge, largest scale more than a 

moderate allows otherwise FF++ is 
Meta/AWS) hosted hosting/license 

historically) terms deepfake set student project the better 
imbalance 

available needs for a proof- time/effort 
of-concept tradeoff 

5. Deepfake Detection — Audio 

Academic-
Dataset Source License Size Label quality Class 

imbalance project fit Verdict 

BEST — directly 
High — the 

Documented matches audio 
~120,000+ standard 

ASVspoof 2019 / 2021 ASVspoof Free for research bona-fide vs. Yes — the deepfake detection, 
utterances academic 

(Logical & Physical Challenge use, standard spoof split, field-standard well-documented, 
across benchmark for 

Access) official site academic dataset some imbalance benchmark widely used in the 
editions synthetic/spoofed 

speech detection by attack type literature you already 
reviewed 

High — purpose-
built for vocoder- Generated-only; 

~100,000+ Excellent SECOND 
artifact-style needs pairing 

Official GitHub generated dataset specifically 
detection with a real-

Yes, paired for the vocoder-
WaveFake release (research Free, open, audio clips 

(matches your speech corpus 
paper companion research use across several with LJSpeech detection sub-task 

proposal's (e.g., LJSpeech) 
dataset) TTS/vocoder your architecture 

methods 'Vocoder Artifact for the bona-fide 
names 

Detection' step class 
directly) 

N/A — this is 
Yes, as the Use only as the 'real' 

Official High, clean, the bona-fide-
LJSpeech (real-speech real-speech class complement to 
complement) LJSpeech release Public domain 13,100 clips, 

half of a WaveFake/ASVspoof, 
(Keith Ito) ~24 hours single-speaker class source, not 

studio recordings a classification 
pairing not standalone 

dataset itself 

Use 
ASVspoof/WaveFake 

Availability 
Not fully as your primary 

Referenced in the depends on that 
AVLips (from your specified in Unknown choice; treat AVLips 

QPAIN 2025 paper's release 
literature review's the abstract without the full Unknown Only if you can 

paper confirm access as a 'nice to have' only 
deepfake paper) paper you terms — verify 

you have if you can get the full 
already reviewed before 

committing access to paper and confirm the 
data is actually 
downloadable 

6. Deepfake Detection — Video 

Dataset Source License Size Label quality Class Academic-
imbalance project fit Verdict 

BEST starting point 
— reuse the same 
dataset as your 

FaceForensics++ 1,000 original image pipeline, 
(video-level, same TU Munich Free, research 

agreement + manipulated High Balanced across 
methods Yes extracting temporal 

source as image table) videos sequences instead of 
single frames, 
which saves real 
setup effort 

Fake-heavy at 
Celeb-DF v2 (video- Official project 

page Free, research use ~590 real + 
level) 5,600 fake High video count but Yes Good generalization 

test set, same as the 
usable for 

Page 23 of 48 



TrustNet AI — Engineering Blueprint 

Dataset Source License Size Academic-
Label quality Class 

imbalance project fit Verdict 

temporal- image-pipeline 
consistency and recommendation 
lip-sync tasks 

High — 
specifically 

Valuable 
designed to test 

specifically for 
robustness under 

60,000 videos, testing whether your 
Free for academic real-world video 

Official controlled video pipeline holds 
research, degradation, 

DeeperForensics-1.0 GitHub/project perturbations Documented Yes, if access is 
directly relevant 

page registration obtained up under 
compression — 

required (compression, 
blur) included to your 

worth pursuing if 
compression-

FF++ alone proves 
robustness 

too clean/easy 
concern for 
rPPG 

Not a deepfake 
Use this only to 

dataset — this is 
validate your rPPG 

a physiological-
Only as a signal-extraction 

signal dataset 
feasibility pipeline in isolation 

Custom small used to sanity-
sanity-check, before deciding 

rPPG/pulse-signal set UBFC-rPPG check whether 
N/A whether to keep 

(e.g., UBFC-rPPG for official release Free, research use Small —42 
not for 

subjects your rPPG 
feasibility testing only) deepfake rPPG as a 

extraction code 
classification committed feature 

works at all 
itself or a stretch goal 

before ever 
(per the earlier risk 

touching 
discussion) 

deepfake video 

OSINT module note: there is no standard benchmark dataset for 'content verification against external sources' — this is 
expected, and matches the literature-gap finding discussed earlier. Build a small, hand-curated evaluation set (20-50 
known-verified and known-fabricated content items with documented ground truth) rather than searching for a benchmark 
that doesn't exist. 

 

Part E-2 — Algorithm Recommendations Per Module 

Module Baseline algorithm Strong algorithm Best practical pick for 
this team Build first Build later Accuracy vs. 

complexity 

Baseline ~90%, hybrid 
Logistic Regression / ~96-97% — the jump 

LightGBM + BERT LightGBM+BERT GNN structural layer, 
Phishing Random Forest on Baseline first, from baseline to hybrid 

(text) hybrid, matching ensemble (skip GNN 
week 8-9 week 12+ if time 

lexical+WHOIS 
features BGL-PhishNet initially — see note) allows is the single best effort-

to-accuracy trade in the 
whole project 

RoBERTa upgrade Baseline ~92-95% (this 
Fine-tuned DistilBERT DistilBERT fine-tuned 

TF-IDF + Logistic and Sentence- task is comparatively 
(lighter, faster to on SMS Spam Baseline first, 

Scam Message Regression / Naive easy), DistilBERT fine-
Bayes train/serve than full week 8-9 Transformer 

Collection + email 
BERT/RoBERTa) corpus, threshold-tuned similarity scoring, tuned ~97%+ achievable 

later on SMS Spam Collection 

SBERT + XGBoost as 
SBERT embeddings + the primary path; Baseline ~80-85%, 

Reviewer-behavior 
TF-IDF + duplicate- XGBoost classifier + Isolation Forest as a SBERT+XGBoost 

Baseline first, graph features 
Fake Review detection heuristics + Isolation Forest for secondary anomaly realistically 88-92% 

week 9-10 (posting frequency, 
Logistic Regression outlier/bot-pattern signal fed into evidence, 

burstiness), later depending on dataset 
detection not the primary noise 

classifier 

EfficientNet-B0 fine-
A small CNN tuned — matches the Baseline ResNet-18 ~80-

EfficientNet-B0/B4 + PRNU/ELA forensic 
(ResNet- literature review's 85% on FF++, 

Deepfake — Grad-CAM, optionally Baseline first, feature fusion, later, 
reference paper exactly EfficientNet-B0 fine-

Image 18/EfficientNet-B0) 
a lightweight ViT if week 10-11 once the semantic 

fine-tuned on FF++ 
compute allows and is far cheaper to tuned ~90%+ achievable 

frames classifier works 
train than a ViT from with modest compute 
scratch 

Page 24 of 48 



TrustNet AI — Engineering Blueprint 

Module Baseline algorithm Strong algorithm Best practical pick for 
this team Build first Build later Accuracy vs. 

complexity 

Baseline SVM-on-
BiLSTM on MFCC — 

MFCC ~75-80%, 
directly matches the Wav2Vec2 fine-

MFCC features + BiLSTM or CNN on BiLSTM ~81-85% 
reviewed paper's tuning (heavier, 

Deepfake — simple classifier MFCC/spectrogram, Baseline first, (matches literature 
approach and is lighter 

Audio (SVM/Random matching your literature week 11-12 higher potential 
range), Wav2Vec2 fine-

ceiling), later if time 
Forest) reference paper to train than a 

transformer-based audio allows tuned can push higher 
but at real compute/time 

model 
cost 

Frame-level reuse of the 
Frame-level CNN/ViT Frame-level rPPG as an explicit image model ~85-90% 
+ basic temporal EfficientNet (reuse the stretch goal (see risk on FF++ video-level 

Frame-level image 
Deepfake — smoothing (majority image model) + blink- Baseline first, register), full aggregation; rPPG's 
Video classifier applied per-

rate heuristic — get this week 12-13 temporal Vision contribution is unproven 
frame, majority-voted vote or simple LSTM 

over frame scores) + working before Transformer only if for your timeline and 
blink/lip-sync heuristics attempting rPPG time allows should not be counted on 

for the demo numbers 

On the GNN component of the phishing module specifically: it is real, precedented, and part of the reference paper's 
97.3% result — but it is also the most implementation-heavy of the three phishing sub-models (graph construction from 
URL structure is nontrivial engineering). The practical recommendation is to get LightGBM+BERT working and 
measured first, and add the GNN as a genuine 'strong algorithm' upgrade only once that baseline is solid, rather than 
attempting all three simultaneously and risking none of them being finished and measured. 

 

Part E-3 — Deepfake Architecture Depth: Image, Audio, Video 

Image 

• Start with: EfficientNet-B0 (or ResNet-18 as an even lighter first pass), pretrained on ImageNet, fine-tuned on 
face-cropped frames. 

• CNN vs. ViT: CNN first. Vision Transformers need substantially more training data or careful pretraining to 
outperform a well-tuned CNN at this data scale, and EfficientNet is exactly what the literature review's reference 
paper used, at a fraction of a ViT's compute cost. A ViT is a legitimate 'later' upgrade, not a 'first' choice. 

• Depth: shallow-to-medium (EfficientNet-B0/B4, not B7; ResNet-18/34, not ResNet-152). A deeper backbone on 
a dataset in the tens-of-thousands-of-images range overfits faster than it learns — matching model capacity to 
data size matters more than chasing the largest available architecture. 

• Preprocessing: face detection + alignment/cropping (MTCNN or mediapipe), consistent resizing, normalization 
matching the pretrained backbone's expected input stats, and light augmentation (flip, slight color jitter, 
compression-artifact simulation since real-world deepfakes are often re-compressed after upload). 

• Feature extraction: let the CNN backbone learn features end-to-end from pixels rather than hand-engineering 
them; add ELA (Error Level Analysis) and frequency-domain features as a parallel, simpler signal if time allows, 
fused late rather than early. 

• Explainability: Grad-CAM is the right fit — it directly localizes which image regions drove the prediction, 
matches your architecture diagram's stated choice, and is cheap to compute at inference time. 

Audio 

• Start with: MFCC feature extraction feeding a BiLSTM — directly matches your reviewed literature paper's 
approach and is well-suited to the temporal nature of speech artifacts. 

• CNN vs. Transformer vs. BiLSTM: BiLSTM first, for the same data-scale reasoning as image — Wav2Vec2 
(transformer-based) is a legitimate, higher-ceiling upgrade but is heavier to fine-tune and needs more 
data/compute to realize its advantage over a well-tuned BiLSTM-on-MFCC baseline. 

Page 25 of 48 



TrustNet AI — Engineering Blueprint 

• Depth: 2-3 BiLSTM layers is a sensible, well-precedented depth for this task — going deeper (5+ layers) on a 
dataset in the ASVspoof/WaveFake size range is far more likely to overfit or simply slow training than to 
meaningfully improve accuracy. 

• Preprocessing: consistent sample-rate resampling, silence trimming, MFCC extraction (13-40 coefficients, 
matching your literature review's finding that specific coefficients like 2 and 9 carry strong discriminative signal 
— worth explicitly checking your own feature importance against that finding). 

• Feature extraction: MFCC as primary; pitch/F0 contour and breathing-pattern features as documented in your 
architecture diagram are reasonable secondary features to fuse in once the MFCC+BiLSTM baseline works. 

• Explainability: per-coefficient or per-time-segment attention weights are the right fit — report which MFCC 
coefficients and which time windows contributed most, directly mirroring the reviewed paper's explainability 
approach. 

Video 

• Start with: reuse the image pipeline's per-frame classifier, run across sampled frames, aggregate via majority vote 
or simple averaging — this is the cheapest path to a working video score and directly reuses Phase 4's earlier 
work. 

• CNN vs. ViT vs. hybrid: frame-level CNN (reused from image) plus a lightweight temporal layer (a small LSTM 
or even a simple moving-average/majority-vote over frame scores) is the sensible depth — a full spatio-temporal 
Vision Transformer is real, precedented in newer research, but is a significant additional training and data 
undertaking that should be a 'later' item, not a 'first' item. 

• Depth: shallow on the temporal side specifically — one recurrent layer over frame-level CNN outputs is enough 
to capture basic temporal inconsistency; this is deliberately not a place to add depth, since the frame-level CNN is 
already carrying most of the discriminative signal. 

• Preprocessing: frame sampling at a fixed rate (e.g., 1-2 frames/second is usually sufficient, not every frame — 
this also keeps inference cost manageable), face detection/tracking per frame, consistent alignment across frames 
so temporal comparison is meaningful. 

• Feature extraction: per-frame CNN embeddings as primary; blink-rate and basic lip-sync offset (audio-video 
timing correlation) as secondary, well-precedented signals worth implementing before rPPG. 

• Explainability: Grad-CAM per representative frame (not every frame — pick the frames the model was least 
confident about or most influential in the aggregate score) plus a simple temporal-consistency plot showing 
frame-by-frame score variation. 

• On rPPG specifically: this is a physiological-signal extraction problem layered on top of an already-hard 
deepfake-detection problem. Validate it in isolation first (see the UBFC-rPPG feasibility dataset in Part E-1) 
before wiring it into the main pipeline, and keep it out of the critical path for your MVP video score — this is the 
same guidance given earlier in this project's discussion and it's worth repeating here as an explicit architectural 
decision, not just a caution. 

 

Part E-4 — Per-Model Input/Pipeline/Deployment Summary 

Evaluation Deployment Explainability 
Module Input format Preprocessing Training strategy Validation 

strategy metrics constraints output 

Fine-tune BERT on Sub-second 
Tokenize URL Stratified k-fold Accuracy, 

URL string (+ labelled text, train inference required; Evidence list of 
components, extract cross-validation Precision, Recall, 

option LightGBM on tabular LightGBM is fast, suspicious URL 
Phishing ally 

WHOIS/SSL (k=10, matching F1, ROC-AUC — 
fetched page features separately, BERT inference is tokens + flagged 

the reference report all five, not 
HTML) metadata, 

clean/normalize combine via weighted 
paper) accuracy alone the bottleneck — metadata fields 

voting consider ONNX 

Page 26 of 48 



TrustNet AI — Engineering Blueprint 

Evaluation Deployment Explainability 
Module Input format Preprocessing Training strategy Validation 

strategy metrics constraints output 

export or 
DistilBERT if 
latency matters for a 
live demo 

Lowercase/clean Fine-tune 
Very light — Highlighted 

(lightly — DistilBERT with a Accuracy, 
DistilBERT is fast phrases/tokens 

transformers handle classification head, Held-out Precision, Recall, 
Scam Raw user-typed enough for real-time driving the 

standard cross- validation split, 
text case reasonably F1 (F1 matters 

Message typing-assistant- classification 
well), tokenize via entropy loss with stratified by class most given class 

imbalance) style use if ever (attention-weight 
the model's own class weighting for 

needed based) 
tokenizer imbalance 

Accuracy, 
Precision, Recall, 

Review text + SBERT embeddings Stratified k-fold, F1, plus manual 
Clean text, compute Which features 

reviewer → XGBoost plus a held-out spot-check of 
duplicate/near- Light — SBERT (duplicate score, 

metadata classifier; Isolation cross-dataset test borderline cases 
Fake duplicate similarity embedding + sentiment 

Forest run in parallel 
Review (posting (train on one (fake-review 

scores, extract XGBoost inference mismatch, burst 
frequency, on behavioral dataset, validate on labels are 

behavioral features is fast pattern) drove the 
account age if another) to check inherently noisier 

separately features for anomaly 
flag 

available) flagging generalization than 
phishing/deepfake 
labels) 

Held-out split 
Fine-tune Accuracy, GPU strongly 

from the same 
Face EfficientNet-B0 Precision, Recall, preferred for 

dataset + a cross- Grad-CAM 
detection/alignment, pretrained on F1, ROC-AUC, training; inference 

Deepfake Image file dataset test (FF++ heatmap + which 
and cross-dataset can run on CPU with 

— Image (JPEG/PNG) resize, normalize to ImageNet, standard 
trained, Celeb-DF facial region was 

backbone's augmentation, early accuracy reported acceptable latency if 
tested) to honestly flagged 

expected stats stopping on separately and the model is small 
validation loss report 

generalization honestly (B0) 

Held-out split, 
ideally cross-

Resample to a dataset Light — MFCC 
Train BiLSTM (2-3 Which MFCC 

Audio file consistent rate, trim (ASVspoof- Accuracy, extraction + 
Deepfake layers) on MFCC coefficients / time 

silence, extract trained, Precision, Recall, BiLSTM inference 
— Audio (WAV/MP3, 

resampled) sequences, cross- segments were 
MFCC (13-40 F1, ROC-AUC is fast, real-time-
coefficients) entropy loss WaveFake-tested) 

for honest capable most influential 
generalization 
reporting 

Video-level held-
out split (never Video-level 

Reuse the fine-tuned split frames from Accuracy, Heaviest of the three 
Frame sampling (1- image model per the same video Precision, Recall, — frame sampling Representative-
2 fps), face frame, aggregate via across train/test — F1, ROC-AUC — rate directly trades frame Grad-CAM 

Deepfake Video file detection/tracking, majority vote/small this leaks always at the off latency vs. + temporal 
— Video (MP4 etc.) per-frame alignment temporal layer; information and video level, not accuracy; this is the consistency plot + 

matching the image blink/lip-sync inflates reported frame level, since module most likely blink-rate/lip-
pipeline heuristics computed accuracy, a that's what a user to need GPU at sync evidence 

separately common mistake actually cares inference time too 
worth avoiding about 
explicitly) 

Video-level train/test splitting deserves repeating on its own: never let frames from the same source video appear in both 
the training and test sets. This is the single most common evaluation mistake in student deepfake-detection projects, and it 
silently inflates reported accuracy in a way that will not survive a panelist asking 'how did you split your data.' 

 

Part E-5 — Research Roadmap & Overall Strategy 

• Phase 1 — Dataset selection (weeks 1-2): confirm every chosen dataset actually downloads, loads, and matches 
its documented label scheme; flag any access-gated datasets (FF++, Celeb-DF) and request access immediately 
since approval can take days to weeks. 

Page 27 of 48 



TrustNet AI — Engineering Blueprint 

• Phase 2 — Baseline model (weeks 3-9, staggered per module per the build order above): the simplest viable 
model per module, evaluated honestly, numbers recorded — this is the safety net that guarantees you have 
*something* measured even if the 'strong' model never gets finished. 

• Phase 3 — Improved model (weeks 8-14, staggered): the 'strong algorithm' column from Part E-2, built only after 
the baseline is working and measured, never in parallel with an unfinished baseline. 

• Phase 4 — Integration (weeks 12-16): wrap each finished model behind the predict() interface (Part D) and wire 
into the Kafka pipeline, one module at a time. 

• Phase 5 — Testing (weeks 15-17): cross-dataset generalization checks, load testing, the full test pyramid from 
Part M. 

• Phase 6 — Deployment (week 18): containerize, deploy, document. 

What to build first if time is genuinely limited 

• Easiest modules, build first: Phishing, Scam Message — smallest datasets, fastest training cycles, most 
precedented architectures, cheapest to get real numbers from. 

• Medium-difficulty: Fake Review, Deepfake-Image — moderate dataset/setup complexity, well-precedented but 
need more careful evaluation design (cross-dataset checks, label noise awareness). 

• Hardest: Deepfake-Audio, Deepfake-Video, OSINT — audio and video need more compute and more careful 
preprocessing; OSINT has no standard benchmark and depends on external services. 

MVP vs. future scope — direct recommendation 

• MVP (must work, measured, and demoable): Phishing, Scam Message, Fake Review, Deepfake-Image, 
Deepfake-Audio, Trust Score Engine v1 (weighted average fusion), basic Explainable AI output, core dashboard. 

• Stretch goals (build if time allows, not required for panel defense): Deepfake-Video beyond frame-level reuse, 
rPPG specifically, Trust Score Engine's contradiction-detection layer, full OSINT verification against multiple 
external sources, full Kubernetes deployment (Docker Compose is sufficient for MVP). 

• Explicit future scope (documented, not attempted this year): Telegram/WhatsApp/Email scanner adapters, 
browser extension, mobile app, enterprise API tier — all designed for structurally in Part Q, none required to be 
built. 

 

Part R — Technology Decision Guide 

One row per layer, organized to answer the question directly: what to use, why, what it replaces, and what the honest 
verdict is for a four-person student team specifically. The guiding principle stated at the top of this document is applied 
consistently here: minimum tool count that still gets a genuinely production-shaped architecture, not maximum tool 
count that looks impressive on a slide. 

Verdict for this 
Layer Recommended Why / alternatives considered Free/OSS Difficulty (1-10) 

team 

Keep — already 
Component-based UI, type 

chosen, well-
safety catches bugs before 

supported, huge 
Frontend React 19 + TypeScript + Tailwind CSS runtime, Tailwind avoids hand- Free/OSS 4 

community, 
rolled CSS sprawl | Alternatives: 

matches your 
Vue, Svelte 

existing proposal 

Async-native (matches Kafka's Keep — the right 
Backend 

FastAPI async nature well), automatic Free/OSS 3 choice for this 
framework 

OpenAPI docs, Pydantic project's shape; 

Page 28 of 48 



TrustNet AI — Engineering Blueprint 

Verdict for this 
Layer Recommended Why / alternatives considered Free/OSS Difficulty (1-10) 

team 

validation built in, fast to write | Django adds an 
Alternatives: Django REST, ORM/admin you 
Flask don't need, Flask 

lacks async and 
validation out of 
the box 

Custom FastAPI 
gateway for MVP 

Central auth/routing/rate- — a dedicated 
limiting choke point | product like Kong 

FastAPI app acting as gateway 
Alternatives: Kong (more 5 (custom) / 6 is real overkill for 

API Gateway (custom) or Kong/Traefik if you want Free/OSS 
features, more ops overhead), (Kong) a 4-person team's 

a dedicated gateway product 
Traefik (simpler, good with request volume; 
Docker/K8s) revisit only if 

scaling to real 
production traffic 

Self-hosted JWT 
Industry-standard, well- — building it 
documented, no reinventing yourself (with a 

python-jose or PyJWT for JWT, crypto | Alternatives: well-tested library, 
Authentication passlib/argon2-cffi for password Auth0/Clerk (managed, but paid Free/OSS 4 not from scratch 

hashing at scale and adds an external crypto) is exactly 
dependency for a project meant the kind of learning 
to demonstrate you built auth) a B.E. project 

should demonstrate 

Simple, explainable, no external Custom RBAC — 
service dependency | OPA is genuinely 

Authorization Custom role-based checks via FastAPI 
Alternatives: Open Policy Agent Free/OSS 3 enterprise-grade 

(RBAC) dependencies 
(OPA) — real but heavy for this but is unnecessary 
scale complexity here 

Plain FastAPI 
wrapper — 

Simplicity — a FastAPI route 
Triton/TorchServe 

that loads a model and calls 
solve multi-model 

Plain FastAPI endpoints wrapping .predict() is sufficient at this 
3 (FastAPI) / 7 GPU-sharing 

AI model serving loaded models (TorchServe/Triton scale and keeps every service Free/OSS 
(Triton) problems you don't 

only if truly needed) uniform | Alternatives: 
have yet; adopting 

TorchServe, NVIDIA Triton, 
them now is 

BentoML 
complexity without 
payoff 

Best-documented, most tutorials, PyTorch + HF — 
PyTorch + Hugging Face 

matches every reference paper's the ecosystem 
Transformers (for 

tooling | Alternatives: match with your 
AI training BERT/DistilBERT/RoBERTa), scikit- Free/OSS 5 

TensorFlow/Keras (equally literature review's 
learn/XGBoost/LightGBM for tabular 

valid, less momentum in current papers alone makes 
models 

NLP tooling) this the right call 

Tracks which run produced Free MLflow — self-
which checkpoint, compares (MLflow hosted means no 
metrics across experiments — fully; account/quota 

MLOps / 
MLflow (self-hosted, free) or Weights directly supports the W&B free limits for a team; 

experiment 4 
& Biases (free tier) experiments/ folder design in tier W&B's free tier is 

tracking 
Part D | Alternatives: Neptune.ai, sufficient also a legitimate, 
Comet — both fine, less for student slightly easier-to-
commonly free at this scale use) start alternative 

Start with a 
manifest.json 

Tracks which dataset version approach — add 
trained which model without DVC only if 

DVC (Data Version Control) or simply 
Dataset committing large files to git | 5 (DVC) / 2 dataset versioning 

a documented manifest.json + S3/local Free/OSS 
management Alternatives: Full feature stores (manifest) problems actually 

storage 
(Feast) — real overkill for this start occurring; 
project's scale don't adopt a 

heavier tool 
preemptively 

Page 29 of 48 



TrustNet AI — Engineering Blueprint 

Verdict for this 
Layer Recommended Why / alternatives considered Free/OSS Difficulty (1-10) 

team 

Manifest-based, 
Answers 'which checkpoint is 

upgrading to 
A simple checkpoints/ folder + currently deployed and why' 

MLflow's registry 
manifest.json (per Part D) — without needing a dedicated 

Model registry Free/OSS 2-4 naturally if 
MLflow's built-in registry if already product | Alternatives: MLflow 

MLflow is already 
using MLflow Model Registry, full registry 

adopted for 
products 

tracking 

This project's features are 
computed at inference time per-

Skip entirely — 
request, not shared across many 

Feature store Not needed — — explicitly correct to 
models at scale — a feature store 

omit, not a gap 
solves a problem you don't have | 
Alternatives: Feast 

Pydantic covers request 
Pydantic (already part of FastAPI) for 

validation; dataset-level Pydantic is 
API-level validation; Great 

Data validation validation is a nice-to-have, not Free/OSS 2 (Pydantic) sufficient for MVP 
Expectations only if dataset-quality 

core | Alternatives: Great scope 
checks become a real pain point 

Expectations, Pandera 

Standard, well-documented, 
everything downstream Pillow + OpenCV 

Pillow, OpenCV, torchvision 
Image processing (MTCNN/mediapipe face Free/OSS 3 — the default, 

transforms 
detection) builds on these | correct choice 
Alternatives: scikit-image 

Purpose-built for exactly the librosa — matches 
MFCC/spectral features your the literature 

librosa (MFCC/feature extraction), 
Audio processing architecture specifies | Free/OSS 4 review's 

torchaudio 
Alternatives: pydub (lighter, less methodology 
feature-rich) directly 

OpenCV + ffmpeg 
— more control 

Industry-standard, handles 
matters here given 

OpenCV + ffmpeg (via ffmpeg-python virtually any input format/codec 
Video processing Free/OSS 5 frame-sampling-

or subprocess) for frame extraction | Alternatives: moviepy (simpler 
rate tradeoffs 

API, less control) 
discussed in Part 
E-3 

The field standard, pretrained 
Hugging Face — 

checkpoints available for every 
Hugging Face Transformers directly matches 

model your architecture names | 
NLP (BERT/DistilBERT/RoBERTa/SBERT Free/OSS 5 every text-based 

Alternatives: spaCy (better for 
via sentence-transformers) module's 

classic NLP pipelines, less 
architecture 

central here) 

Purpose-built, well-documented 
SHAP (tabular/LightGBM/XGBoost), libraries exist for exactly each SHAP + pytorch-
Grad-CAM implementation via modality's explainability need — grad-cam — both 

Explainable AI pytorch-grad-cam library, attention- no need to hand-roll any of this | Free/OSS 5-6 mature, both 
weight extraction (native to Alternatives: LIME (alternative directly usable off 
Transformers) to SHAP, less commonly used in the shelf 

current practice) 

Build custom — 
correctly identified 

The fusion logic (Part I) is 
Custom Python service (no framework as your core 

project-specific; no off-the-shelf 
Trust Score Engine needed — this is business logic, not a — — novelty, not 

product does cross-modal fraud-
library problem) something to 

score fusion 
outsource to a 
library 

FastAPI 
BackgroundTasks is zero-setup BackgroundTasks 

FastAPI BackgroundTasks for and sufficient for simple cases; for MVP — Kafka 
lightweight fire-and-forget work; avoid adopting Celery's 2 already covers the 

Background jobs Celery only if job complexity grows operational overhead (a broker + Free/OSS (BackgroundTasks) heavy async 
(scheduled/retryable jobs beyond workers) on top of Kafka unless / 6 (Celery) orchestration; a 
Kafka's scope) genuinely needed | Alternatives: second job queue is 

Celery, RQ redundant at this 
scale 

Page 30 of 48 



TrustNet AI — Engineering Blueprint 

Verdict for this 
Layer Recommended Why / alternatives considered Free/OSS Difficulty (1-10) 

team 

Kafka if the team 
Decouples slow AI processing 

has bandwidth to 
from the request path, enables 

Apache Kafka (target architecture) or learn it; RabbitMQ 
multi-consumer fan-out | 7 (Kafka) / 5 

Message queue RabbitMQ (pragmatic MVP substitute, Free/OSS is a completely 
Alternatives: RabbitMQ, Redis (RabbitMQ) 

per Part G note) legitimate 
Streams (lighter but less standard 

substitute if not — 
for this event volume/pattern) 

see Part G 

Sessions, rate-limit counters, 
hot-scan cache — exactly the 

Redis — also 
ephemeral, high-read-frequency 

doubles as the 
Caching Redis data Redis is built for | Free/OSS 3 

session store, 
Alternatives: Memcached (less 

reducing tool count 
feature-rich, no native data 
structures beyond key-value) 

Strong consistency, mature, 
excellent with 

PostgreSQL — 
SQLAlchemy/FastAPI 

Relational matches your 
PostgreSQL ecosystem | Alternatives: Free/OSS 4 

database proposal, no reason 
MySQL (equally valid, slightly 

to deviate 
less feature-rich for JSON 
columns/advanced indexing) 

Schema flexibility for 
MongoDB — 

heterogeneous AI outputs (Part F Free/OSS 
Document correct fit for the 

MongoDB rationale) | Alternatives: (self- 4 
database data shape 

Firestore (managed but hosted) 
described in Part F 

proprietary/paid at scale) 

S3-compatible API means code 
never changes between local dev Free/OSS MinIO locally, S3 
and cloud deployment — (MinIO) / (or MinIO again) 

MinIO (self-hosted, S3-compatible) for 
genuinely valuable, not just Paid in deployment — 

Object storage local/dev; AWS S3 for actual 3 
convenient | Alternatives: Local (AWS S3, the S3-API-

deployment 
filesystem storage (works for a has a free compatibility is the 
demo, not a real architecture tier) whole point 
story) 

Skip for MVP — 
Not needed for MVP — Postgres full- Elasticsearch/OpenSearch solve 

correctly deferred, 
text search or Mongo text indexes are a scale-of-search problem this 

not a gap; revisit 
Search engine sufficient for the current scope (no project doesn't have yet | — — 

only if a dedicated 
free-text search over millions of Alternatives: Elasticsearch, 

search feature is 
documents required) OpenSearch, Meilisearch 

added later 

Structured logs are what makes 
Structured JSON 

centralized log search useful at 
Structured JSON logging (Python's from day one — 

all — plain text logs defeat the 
Logging logging module + python-json-logger) Free/OSS 3 cheap now, 

purpose of centralization | 
shipped to Loki or ELK expensive to 

Alternatives: Plain text logging 
retrofit 

(avoid) 

The de facto open-source 
standard, huge community, 

Prometheus + 
FastAPI has ready-made 

Grafana — 
instrumentation libraries 

Monitoring/metrics Prometheus + Grafana Free/OSS 5 matches your 
(prometheus-fastapi-

proposal, correct 
instrumentator) | Alternatives: 

choice 
Datadog (excellent but 
paid/proprietary) 

Loki is the 
pragmatic MVP 

Loki is deliberately designed to recommendation 
be cheaper to operate than given team size; 

Grafana Loki (lighter) or the full ELK Elasticsearch while integrating ELK remains valid 
Centralized 

stack (heavier but matches your natively with Grafana (same Free/OSS 4 (Loki) / 7 (ELK) to present as the 
logging 

proposal) dashboards as your metrics) | documented target 
Alternatives: ELK if you want to keep 
(Elasticsearch/Logstash/Kibana) it in the 

architecture 
diagram 

Page 31 of 48 



TrustNet AI — Engineering Blueprint 

Verdict for this 
Layer Recommended Why / alternatives considered Free/OSS Difficulty (1-10) 

team 

Zero additional tool to learn if 
already running Grafana | Grafana Alerting 

Grafana Alerting (built into Grafana, 
Alternatives: — sufficient and 

Alerting no extra tool) or Prometheus Free/OSS 3 
PagerDuty/Opsgenie (paid, already in your 

Alertmanager 
enterprise-scale incident routing stack 
you don't need) 

WeasyPrint lets you design the 
report as HTML/CSS (familiar, 

WeasyPrint — 
flexible) and render to PDF — 

faster to build a 
Report generation WeasyPrint (HTML/CSS to PDF) or faster to iterate on visual design 4 (WeasyPrint) / 6 

Free/OSS good-looking 
(PDF) ReportLab than ReportLab's programmatic (ReportLab) 

report with a small 
API | Alternatives: ReportLab 

team 
(more control, steeper learning 
curve) 

Built-in, no extra dependency, 
Native FastAPI — 

File upload FastAPI's native UploadFile + handles large files via streaming 
Free/OSS 3 no reason to add a 

handling streaming to S3/MinIO rather than loading fully into 
library for this 

memory 

ClamAV self-
Free, well-established, catches 

hosted for the core 
known-malware signatures in 

MVP story; 
ClamAV (open-source antivirus uploaded files before they're 

Free/OSS VirusTotal API as 
Malware scanning engine, run as a sidecar service processed further | Alternatives: 6 

(ClamAV) a nice-to-have 
scanned via clamd) VirusTotal API (paid at volume, 

supplementary 
but has a free tier usable for a 

check if API quota 
student project's scan rate) 

allows 

Type-safe config, validated at pydantic-settings 
pydantic-settings, reading from .env startup rather than failing deep — already implied 

Configuration 
files locally and environment variables inside business logic | Free/OSS 2 by using 

management 
/ K8s ConfigMaps in deployment Alternatives: python-decouple FastAPI/Pydantic, 

(simpler, less type-safe) no extra tool 

Environment 
Simple, well-understood, 

variables + 
Environment variables + .env (local), sufficient for this project's threat 

platform-native 
Secret Kubernetes Secrets or Docker secrets model and team size | 2 (env vars) / 8 

Free/OSS secrets — Vault is 
management (deployment) — a dedicated vault only Alternatives: HashiCorp Vault (Vault) 

correctly out of 
if genuinely needed (real, but genuinely enterprise-

scope for this 
scale overhead) 

project size 

Industry standard, huge 
documentation base, every team 
member likely already has some Docker — no 

Docker / Compose Docker + Docker Compose Free/OSS 4 
exposure | Alternatives: Podman reason to deviate 
(viable alternative, smaller 
community) 

k3s is a genuinely production-
grade but far lighter-weight 
distribution, appropriate for 

k3s for validation, 
k3s (lightweight) for local/demo validating manifests without a 

Docker Compose 
validation; full-manifest design as heavy cluster setup | 

Kubernetes Free/OSS 8 for the actual 
documented target (per Part J honesty Alternatives: minikube (also 

running demo — 
note) fine, slightly heavier), full 

see Part J 
managed K8s (AWS EKS/GKE 
— real cost, unnecessary for a 
demo) 

TLS termination, request routing 
to the Gateway, well-
documented, matches your NGINX — 

Reverse proxy NGINX proposal | Alternatives: Traefik Free/OSS 4 matches your 
(more automatic with proposal, keep it 
Docker/K8s labels, slightly 
different mental model) 

Free for public/student repos, Free (for GitHub Actions — 
CI/CD GitHub Actions tightly integrated with GitHub your 4 matches your 

(where your code already lives), usage tier) proposal, correct 

Page 32 of 48 



TrustNet AI — Engineering Blueprint 

Verdict for this 
Layer Recommended Why / alternatives considered Free/OSS Difficulty (1-10) 

team 

no separate account/tool needed | choice, lowest 
Alternatives: GitLab CI, Jenkins setup friction 
(self-hosted, real operational 
overhead a 4-person team doesn't 
need) 

pytest is the Python standard, 
huge plugin ecosystem (pytest- pytest + Locust — 
asyncio for FastAPI's async both Python-

pytest (backend), Locust or k6 (load routes); Locust is Python-native 3 (pytest) / 5 native, minimizing 
Testing framework Free/OSS 

testing) (easy for the team to script) vs. (Locust) the number of 
k6's JS | Alternatives: unittest languages the team 
(built-in but more verbose), juggles 
JMeter (heavier, GUI-based) 

Free, automatic, catches known-
CVE dependencies and common 

Dependabot (built 
pip-audit / Dependabot (dependency insecure patterns (e.g., use of 

into GitHub, zero 
Security scanning vulnerabilities), Bandit (static analysis eval, hardcoded secrets) before Free/OSS 3 

setup) + Bandit in 
for common Python security issues) they ship | Alternatives: Snyk 

CI 
(more features, has a free tier but 
pushes toward paid at scale) 

Every route is documented 
automatically from your 

Use what FastAPI 
Pydantic schemas and docstrings 

FastAPI's automatic already gives you 
API — this is one of FastAPI's Free 

OpenAPI/Swagger docs (built-in, zero 1 — do not duplicate 
documentation biggest practical advantages | (built-in) 

extra work) this effort 
Alternatives: Manually written 

manually 
Postman collections (redundant 
given FastAPI's built-in docs) 

ruff has largely replaced 
flake8+isort+pylint as the fast, 

ruff + black — fast 
ruff (linting, very fast) + black modern standard; black removes 

to set up, fast to 
Code quality (formatting) + mypy (optional type formatting debates entirely | Free/OSS 2 

run, low ongoing 
checking) Alternatives: flake8 + isort + 

friction 
pylint (older, slower, more 
config) 

Per-service requirements.txt 
keeps each service's 
dependencies isolated (Part N's Per-service 
version-conflict risk mitigation) requirements.txt 

uv or pip + requirements.txt per and is the lowest-friction option with pip — 
Dependency 

service (poetry if the team prefers a for a team new to Python Free/OSS 2 (pip) / 5 (poetry) simplest option 
management 

lockfile-based workflow) packaging | Alternatives: Poetry that still satisfies 
(more features, another tool to the isolation goal 
learn), Conda (heavier, more from Part N 
relevant for pure data-science 
environments than services) 

Skip for MVP, 
Not required for MVP — Docker Terraform solves repeatable name it as a 
Compose files and K8s manifests cloud-provisioning problems; a documented future 

Infrastructure as checked into infra/ are sufficient student project deploying to one step if cloud 
Free/OSS 7 

Code documentation of infrastructure; demo environment doesn't have deployment 
Terraform only if actually provisioning that problem yet | Alternatives: matures beyond a 
cloud resources repeatedly Terraform, Pulumi single demo 

environment 

Matches the honest Docker-
Compose-first guidance from 

A single VM (AWS EC2 free tier / Part J — a full managed 
Single VM + 

Azure student credits / a college Kubernetes service (EKS/GKE) 
Cloud deployment Free tier 3 (single VM) / 8 Docker Compose 

server) running Docker Compose for has real monthly cost that doesn't 
target available (managed K8s) for the actual 

the demo; document the K8s path as fit a student project budget | 
deployed demo 

the scaling story Alternatives: AWS EKS, GCP 
GKE, Azure AKS (all real, all 
costly at this project's stage) 

 

Page 33 of 48 



TrustNet AI — Engineering Blueprint 

Part S — Developer Toolkit 

Deliberately minimal — every tool below either has no realistic free/simple substitute for its job, or was chosen 
specifically because it consolidates two needs into one tool (Grafana for both metrics and logs; DBeaver for both 
relational and document databases). 

Category Recommended tool(s) Why 

Free, huge extension ecosystem, works well across 
IDE VS Code 

Python/TS/YAML/Docker all in one editor 

Python, Pylance, Docker, YAML, 
Covers backend dev, container editing, quick API 

VS Code extensions Thunder Client (or REST Client), 
testing, and git blame/history without leaving the editor 

GitLens, Even Better TOML 

Git CLI + GitHub Desktop (optional, for CLI is the source of truth; GUI tools are optional comfort 
Git tooling members less comfortable with CLI) + layers, not a dependency the team should rely on 

GitLens in VS Code exclusively 

Thunder Client (VS Code extension) or Thunder Client stays inside the editor, reducing tool-
API testing 

Postman (free tier) switching; Postman is fine if the team already knows it 

DBeaver alone covers both relational and (with plugin) 
DBeaver (free, works with Postgres and 

document DB browsing, reducing tool count; MongoDB 
Database GUI has plugins for Mongo) or pgAdmin 

Compass is the official, very polished alternative for 
(Postgres-specific) + MongoDB Compass 

Mongo specifically 

Kafdrop or Redpanda Console (both free, Essential once Kafka work starts — without this, 
Kafka UI both give topic/consumer-group debugging 'why didn't my consumer receive the event' is 

visibility) done blind 

Lets you inspect cached keys/sessions directly, useful for 
Redis GUI RedisInsight (free, official) 

debugging cache-related bugs 

Docker Desktop (free for 
Docker Desktop is the default; OrbStack is a genuinely 

Docker Desktop personal/student/small-team use) or 
faster, lighter alternative specifically on macOS if any 

alternative OrbStack (macOS, faster, also has a free 
team member is on Mac 

tier) 

k9s is worth learning — it's fast, keyboard-driven, and 
k9s (terminal-based, fast) or the official 

Kubernetes dashboard works identically whether you're on k3s locally or a real 
Kubernetes Dashboard 

cluster later 

Grafana (via Loki, already in the stack) 
Reusing Grafana for both metrics and logs (Loki) keeps 

Log viewer — avoid adding a separate dedicated log-
the team looking in one place instead of three 

viewer tool 

One tool, multiple data sources (Prometheus + Loki) — 
Monitoring dashboards Grafana (already chosen) 

deliberately minimizing tool count here 

TensorBoard (built into PyTorch 
Both are free and already implied by the MLOps choice 

Model visualization workflows) or MLflow's built-in UI if 
in Part R — no separate tool needed 

MLflow is adopted 

Label Studio (free, open-source, supports Most modules use pre-labelled public datasets (Part E-1); 
text/image/audio annotation) — only if Label Studio is worth having ready only for the OSINT 

Annotation / labeling 
you need to hand-label anything beyond hand-curated evaluation set or any label-quality spot-
the public datasets checking 

Deliberately avoiding a heavier dedicated tool unless the 
Dataset management A manifest.json + S3/MinIO, per Part R 

manifest approach proves insufficient 

draw.io (free, works as a VS Code draw.io for the formal diagrams that go in the final 
UML / architecture 

extension too) or Excalidraw for quicker report; Excalidraw for fast whiteboard-style sketches 
diagrams 

sketches during design discussions 

Markdown files in docs/ (this document's Plain Markdown in-repo is sufficient for MVP; a docs 
Documentation 

source structure) + MkDocs or site is a nice-to-have, not a requirement 

Page 34 of 48 



TrustNet AI — Engineering Blueprint 

Category Recommended tool(s) Why 

Docusaurus only if the team wants a 
browsable docs site 

GitHub Projects (free, built into the same 
GitHub Projects keeps issue tracking and code in one 

Project management platform as your code) or Trello (free 
platform, reducing context-switching for a small team 

tier) 

 

Recommended installation order 

• 1. Git, Python 3.11+, Node.js (for the frontend and for docx/tooling scripts), Docker Desktop — the four things 
every team member needs before writing a single line of project code. 

• 2. VS Code + the extension set above. 

• 3. Clone the repo, run docker-compose up for infra-only (Postgres/Mongo/Redis/Kafka) — confirms the local 
environment works before any service code is written. 

• 4. Per-service Python virtual environment + pip install -r requirements.txt for whichever service that team 
member owns. 

• 5. Database GUI (DBeaver/Compass) + Kafka UI (Kafdrop) + RedisInsight — connect to the now-running local 
infra to visually confirm everything is reachable. 

• 6. API testing tool (Thunder Client/Postman) configured against the local Gateway once it exists. 

• 7. MLflow (or W&B account) — set up once the first model training script exists, not before. 

Common beginner mistakes per tool, worth flagging early 

• Docker: forgetting to add a .dockerignore, resulting in enormous build contexts and slow builds — set this up in 
week 5, not discovered in week 15. 

• Kafka: forgetting consumer group IDs, causing every service restart to reprocess all historical messages, or 
conversely to silently skip messages — get one working example understood deeply before wiring five detectors. 

• FastAPI: putting business logic directly in route handlers instead of the service layer (Part E) — this is the single 
most common structural drift in student FastAPI projects and it's why the layered folder discipline is worth 
enforcing in code review. 

• Git: large model checkpoint files accidentally committed to git history — set up .gitignore for checkpoints/ 
before the first training run produces one, since removing a large file from git history after the fact is a genuinely 
painful cleanup. 

• PyTorch/training: forgetting model.eval() during inference (leaves dropout/batchnorm in training mode, silently 
degrading prediction quality) — this is a one-line bug that produces confusingly bad results with no error 
message. 

 

 

 

 

 

 

 

Page 35 of 48 



TrustNet AI — Engineering Blueprint 

1. Project Overview 

TrustNet AI is a microservices-based digital trust platform with 16 backend services, 7 isolated AI model pipelines, an event-
driven Kafka backbone, and a fused Trust Score output. This document is the single source of truth for repo structure, service 
internals, database layer, CI/CD, and API contracts. 

 

2. Full Repository Tree 

trustnet-ai/ 

├── README.md 

├── docker-compose.yml 

├── docker-compose.prod.yml 

├── .env.example 

├── .gitignore 

├── Makefile 

├── .github/ 

│   └── workflows/                     # see Section 6 — CI/CD 

│ 

├── frontend/ 

│   ├── index.html 

│   ├── package.json 

│   ├── vite.config.ts 

│   ├── tailwind.config.js 

│   ├── tsconfig.json 

│   └── src/ 

│       ├── main.tsx 

│       ├── App.tsx 

│       ├── components/ 

│       │   ├── UploadCenter.tsx 

│       │   ├── TrustScoreCard.tsx 

│       │   ├── EvidencePanel.tsx 

│       │   ├── ScanHistoryTable.tsx 

│       │   └── Navbar.tsx 

│       ├── pages/ 

│       │   ├── Dashboard.tsx 

Page 36 of 48 



TrustNet AI — Engineering Blueprint 

│       │   ├── ScanDetail.tsx 

│       │   ├── Login.tsx 

│       │   ├── Reports.tsx 

│       │   └── AdminPanel.tsx 

│       ├── hooks/ 

│       │   ├── useAuth.ts 

│       │   └── useScanStatus.ts 

│       ├── api/ 

│       │   ├── client.ts 

│       │   ├── authApi.ts 

│       │   ├── scanApi.ts 

│       │   └── reportApi.ts 

│       └── store/ 

│           └── authStore.ts 

│ 

├── gateway/ 

│   ├── main.py 

│   ├── Dockerfile 

│   ├── requirements.txt 

│   ├── routers/ 

│   │   ├── auth_proxy.py 

│   │   ├── scan_proxy.py 

│   │   └── report_proxy.py 

│   ├── middleware/ 

│   │   ├── auth_middleware.py 

│   │   ├── rate_limit_middleware.py 

│   │   └── logging_middleware.py 

│   ├── core/app_factory.py 

│   └── config/settings.py 

│ 

├── services/ 

│   ├── auth-service/                        (Pattern A — REST) 

Page 37 of 48 



TrustNet AI — Engineering Blueprint 

│   ├── scan-management-service/             (Pattern A — REST) 

│   ├── report-service/                      (Pattern A — REST) 

│   ├── dataset-service/                     (Pattern A — REST) 

│   ├── analytics-service/                   (Pattern A — REST) 

│   ├── phishing-detection-service/          (Pattern B — Kafka only) 

│   ├── scam-detection-service/              (Pattern B — Kafka only) 

│   ├── review-detection-service/            (Pattern B — Kafka only) 

│   ├── image-deepfake-service/              (Pattern B — Kafka only) 

│   ├── audio-deepfake-service/              (Pattern B — Kafka only) 

│   ├── video-deepfake-service/              (Pattern B — Kafka only) 

│   ├── osint-service/                       (Pattern B — Kafka only) 

│   ├── ai-orchestration-service/            (Pattern C — Hybrid) 

│   ├── trust-engine-service/                (Pattern C — Hybrid) 

│   ├── explainability-service/              (Pattern C — Hybrid) 

│   └── notification-service/                (Pattern C — Hybrid) 

│ 

├── models/ 

│   ├── phishing/ 

│   ├── scam_text/ 

│   ├── fake_review/ 

│   ├── image_deepfake/ 

│   ├── audio_deepfake/ 

│   ├── video_deepfake/ 

│   └── osint/ 

│ 

├── shared/ 

│   ├── schemas/ 

│   │   ├── detection_result.py 

│   │   └── kafka_events.py 

│   ├── auth/verify_token.py 

│   ├── logging/logger_setup.py 

│   ├── constants.py 

Page 38 of 48 



TrustNet AI — Engineering Blueprint 

│   └── exceptions.py 

│ 

├── docker/ 

│   ├── base-python.Dockerfile 

│   └── base-gpu.Dockerfile 

│ 

├── k8s/ 

│   ├── deployments/ 

│   ├── services/ 

│   ├── ingress/ingress.yaml 

│   ├── configmaps/app-config.yaml 

│   ├── secrets-templates/secrets.template.yaml 

│   └── infra/ 

│       ├── postgres-statefulset.yaml 

│       ├── mongo-statefulset.yaml 

│       ├── redis-deployment.yaml 

│       └── kafka-statefulset.yaml 

│ 

├── infra/                                   # Terraform, optional 

│ 

├── scripts/ 

│   ├── init_postgres.sql 

│   ├── init_mongo.js 

│   ├── seed_db.py 

│   ├── generate_test_data.py 

│   └── run_all_evaluations.py 

│ 

├── monitoring/ 

│   ├── prometheus/prometheus.yml 

│   └── grafana/dashboards/ 

│       ├── system-health.json 

│       ├── ai-pipeline.json 

Page 39 of 48 



TrustNet AI — Engineering Blueprint 

│       └── kafka-lag.json 

│ 

├── tests/ 

│   ├── integration/test_scan_to_trust_score_flow.py 

│   └── e2e/test_upload_and_get_score.py 

│ 

├── configs/ 

│   ├── .env.dev.example 

│   └── .env.prod.example 

│ 

└── docs/ 

    ├── architecture/ 

    ├── api-contracts/                       # see Section 7 

    ├── adrs/                                # see Section 8 

    └── runbooks/ 

 

3. Service Internal Layout — All 3 Patterns 

Pattern A — REST services (auth-service, scan-management-service, report-service, dataset-service, analytics-service) 

<service-name>/ 

├── main.py 

├── Dockerfile 

├── requirements.txt 

├── .env.example 

├── routers/            # HTTP route declarations only 

├── controllers/        # parse request → call service → shape response 

├── services/           # business logic 

├── repositories/       # all DB queries live here, nowhere else 

├── schemas/            # Pydantic request/response models 

├── db_models/          # SQLAlchemy table definitions 

├── validators/         # custom validation beyond Pydantic 

├── middleware/error_handler.py 

├── core/app_factory.py 

Page 40 of 48 



TrustNet AI — Engineering Blueprint 

├── config/settings.py 

├── database/ 

│   ├── session.py 

│   ├── base.py 

│   └── migrations/      # Alembic — versions/0001_..., 0002_... 

├── utils/ 

└── tests/ 

Auth-specific extras: services/password_service.py, utils/jwt_helper.py, db_models/user.py, db_models/role.py. 
Scan-Mgmt extras: kafka/producer.py, services/orchestration_trigger.py, db_models/scan.py. 
Report-Service extras: services/pdf_generator.py, templates/report_template.html, storage/s3_client.py. 

Pattern B — Pure Kafka consumers (all 5 detectors + OSINT) 

<detector-service-name>/ 

├── main.py              # starts Kafka consumer loop; no REST router 

├── Dockerfile 

├── requirements.txt 

├── kafka/ 

│   ├── consumer.py      # consumes detection.requested.<type> 

│   └── producer.py      # publishes detector.<name>.completed 

├── controllers/<name>_controller.py 

├── services/<name>_service.py     # calls models/<modality>/inference/predict.py 

├── repositories/result_repository.py   # writes to MongoDB 

├── schemas/detection_result_schema.py 

├── middleware/error_handler.py    # on failure → publishes to <topic>.dlq 

├── core/consumer_factory.py 

├── config/settings.py 

├── database/{mongo_client.py, indexes.py} 

├── health/health_router.py        # tiny FastAPI app, /health /ready only, for K8s probes 

└── tests/ 

Pattern C — Hybrid (ai-orchestration-service, trust-engine-service, explainability-service, notification-service) 

trust-engine-service/ 

├── main.py 

├── kafka/{consumer.py (wildcard detector.*.completed), producer.py (trust_score.generated)} 

├── services/ 

Page 41 of 48 



TrustNet AI — Engineering Blueprint 

│   ├── fusion_service.py           # normalize + weighted combine 

│   ├── contradiction_service.py    # cross-modal disagreement detection 

│   └── risk_mapping_service.py     # score → Low/Medium/High/Critical 

├── repositories/trust_score_repository.py 

├── db_models/trust_score.py 

├── database/{session.py, migrations/} 

├── config/{settings.py, fusion_weights.yaml} 

├── routers/trust_score_router.py   # GET /trust-score/{scan_id} for frontend 

└── tests/ 

(ai-orchestration-service, explainability-service, notification-service follow the same hybrid shape — Kafka in, a thin REST 
endpoint out where the frontend needs to poll/read something directly.) 

 

4. Database Layer 

• PostgreSQL (owned per-service, each with its own Alembic migrations/): users, roles (Auth) · scans (Scan Mgmt) · 
trust_scores (Trust Engine) · reports (Report) · notifications (Notification). 

• MongoDB (schema-flexible, indexes.py per writing service): detection_results, explanations, osint_metadata, 
audit_logs. 

• Redis: sessions, refresh-token blocklist, rate-limit counters, URL-scan cache, in-flight orchestration state 
(caching/redis_client.py per service that needs it). 

• Bootstrap scripts: scripts/init_postgres.sql, scripts/init_mongo.js, scripts/seed_db.py. 

 

5. Model Folders (all 7, identical skeleton, different files inside) 

models/<modality>/ 

├── data/manifest.json 

├── preprocessing/ 

├── training/{train_*.py, hyperparams.yaml} 

├── experiments/<date>_run<n>/ 

├── checkpoints/{manifest.json, *.pt / *.pkl} 

├── inference/predict.py        # the ONLY file other services import 

├── evaluation/{evaluate.py, reports/} 

├── explainability/ 

└── configs/model_config.yaml 

Modality-specific extras: 

Page 42 of 48 



TrustNet AI — Engineering Blueprint 

• phishing/: preprocessing/extract_features.py (WHOIS/SSL/lexical), training/train_bert.py + train_lightgbm.py. 

• scam_text/: training/train_distilbert.py, explainability/attention_extractor.py. 

• fake_review/: preprocessing/duplicate_detector.py, training/train_sbert_xgboost.py + train_isolation_forest.py. 

• image_deepfake/: preprocessing/face_align.py, training/train_efficientnet.py, explainability/gradcam_explainer.py, 
evaluation/cross_dataset_eval.py. 

• audio_deepfake/: preprocessing/mfcc_extractor.py, training/train_bilstm.py, explainability/mfcc_attention.py. 

• video_deepfake/: preprocessing/{frame_sampler.py, face_track.py}, training/train_temporal_head.py (reuses image 
backbone), inference/predict.py calls image_deepfake/inference internally. 

• osint/: unique extra folder sources/{reverse_image_search.py, metadata_crosscheck.py}, 
configs/sources_config.yaml (external API keys). 

 

6. CI/CD — .github/workflows/ 

.github/workflows/ 

├── ci-backend.yml          # runs on every PR touching services/, gateway/, shared/ 

├── ci-frontend.yml         # runs on every PR touching frontend/ 

├── ci-models.yml           # runs model evaluation scripts on every PR touching models/ 

├── docker-build.yml        # builds + pushes images on merge to develop/main 

├── deploy-staging.yml      # auto-deploy to staging on merge to develop 

└── deploy-prod.yml         # manual-trigger deploy to prod on merge to main 

ci-backend.yml — what it actually does, step by step: 

1. Checkout code. 

2. Set up Python 3.11. 

3. Install dependencies per changed service (pip install -r services/<name>/requirements.txt). 

4. Run ruff check + black --check (lint/format gate). 

5. Run bandit -r services/ (security static analysis). 

6. Spin up Postgres/Mongo/Redis as CI service containers. 

7. Run pytest services/<name>/tests/ for every changed service. 

8. Fail the PR if any step fails — this is the gate before merge to develop. 

ci-models.yml: 

1. Checkout code. 

2. Download the relevant checkpoint (from S3/artifact storage, not committed to git). 

3. Run models/<modality>/evaluation/evaluate.py against the held-out test set. 

4. Compare new metrics against the last-known-good metrics in checkpoints/manifest.json. 

Page 43 of 48 



TrustNet AI — Engineering Blueprint 

5. Post the metrics table as a PR comment (accuracy/precision/recall/F1/AUC) — this is what makes "we have real 
numbers" verifiable in your git history, not just claimed in a report. 

docker-build.yml: builds each service's Dockerfile, tags with the git SHA, pushes to a container registry (GitHub Container 
Registry is free and simplest for a student team). 

deploy-staging.yml / deploy-prod.yml: applies the relevant k8s/ manifests (or docker-compose.prod.yml if you're following 
the Compose-first recommendation) to the target environment; deploy-prod.yml requires manual approval (GitHub 
Environments protection rule) rather than auto-deploying. 

 

7. API Contracts — Sample Requests/Responses 

POST /auth/login (Gateway → Auth Service) 

Request: 

json 

{ "email": "alok@example.com", "password": "••••••••" } 

Response 200: 

json 

{ 

  "data": { 

    "access_token": "eyJhbGciOi...", 

    "refresh_token": "8f3a1c2e...", 

    "expires_in": 900, 

    "user": { "id": "u_123", "email": "alok@example.com", "role": "user" } 

  }, 

  "error": null, 

  "meta": { "request_id": "req_9f8e7d" } 

} 

Response 401: 

json 

{ "data": null, "error": { "code": "INVALID_CREDENTIALS", "message": "Email or password is incorrect" }, "meta": { 
"request_id": "req_9f8e7d" } } 

POST /scan (Gateway → Scan Management Service) 

Request (multipart or JSON depending on content type): 

json 

{ 

  "content_type": "url", 

Page 44 of 48 



TrustNet AI — Engineering Blueprint 

  "payload": "http://suspicious-login-page.example", 

  "user_id": "u_123" 

} 

Response 202 (async — scan created, not yet processed): 

json 

{ 

  "data": { "scan_id": "scan_7a1b2c", "status": "pending", "created_at": "2026-08-08T10:15:00Z" }, 

  "error": null, 

  "meta": { "request_id": "req_11aa22" } 

} 

GET /orchestration/{scan_id}/status (frontend polls this) 

Response 200: 

json 

{ 

  "data": { 

    "scan_id": "scan_7a1b2c", 

    "status": "processing", 

    "detectors_expected": ["phishing"], 

    "detectors_completed": [], 

    "progress_percent": 0 

  }, 

  "error": null 

} 

GET /trust-score/{scan_id} (Trust Engine Service, once fusion is done) 

Response 200: 

json 

{ 

  "data": { 

    "scan_id": "scan_7a1b2c", 

    "trust_score": 18, 

    "risk_level": "High", 

    "confidence": 0.94, 

Page 45 of 48 



TrustNet AI — Engineering Blueprint 

    "module_scores": [ 

      { "module": "phishing", "score": 92, "confidence": 0.97 } 

    ], 

    "generated_at": "2026-08-08T10:15:07Z" 

  }, 

  "error": null 

} 

GET /explanation/{scan_id} (Explainability Service) 

Response 200: 

json 

{ 

  "data": { 

    "scan_id": "scan_7a1b2c", 

    "summary": "This URL was flagged as high-risk phishing with 97% confidence. The domain was registered 9 days ago, 
has no valid SSL certificate, and contains the term 'verify-account' in a subdomain designed to imitate a banking login page.", 

    "evidence": [ 

      { "feature": "domain_age_days", "value": 9, "contribution": "high" }, 

      { "feature": "ssl_present", "value": false, "contribution": "high" }, 

      { "feature": "suspicious_subdomain_token", "value": "verify-account", "contribution": "medium" } 

    ] 

  }, 

  "error": null 

} 

Internal Kafka event payload — detector.phishing.completed 

json 

{ 

  "schema_version": 1, 

  "scan_id": "scan_7a1b2c", 

  "detector_type": "phishing", 

  "score": 92, 

  "confidence": 0.97, 

  "label": "phishing", 

Page 46 of 48 



TrustNet AI — Engineering Blueprint 

  "evidence": [ 

    { "feature_or_region": "domain_age_days", "contribution": 0.31, "human_readable_note": "Domain registered 9 days ago" 
}, 

    { "feature_or_region": "ssl_present", "contribution": 0.28, "human_readable_note": "No valid SSL certificate" } 

  ], 

  "metadata": { "model_version": "bert_v1+lgbm_v1", "inference_ms": 340 }, 

  "produced_at": "2026-08-08T10:15:06Z" 

} 

Standard error envelope used by every service, every endpoint: 

json 

{ "data": null, "error": { "code": "SCAN_NOT_FOUND", "message": "No scan found with that id" }, "meta": { "request_id": 
"req_..." } } 

 

8. ADR (Architecture Decision Record) — Template + Filled Examples 

docs/adrs/0001-kafka-vs-rabbitmq.md: 

markdown 

# ADR 0001: Message broker choice — Kafka vs RabbitMQ 

 

## Status: Accepted 

 

## Context 

The system needs async fan-out from Scan Management to multiple independent 

detector services, with at-least-once delivery and consumer-group semantics. 

 

## Decision 

Use RabbitMQ for the actual weeks-6-through-16 build; document Kafka as the 

target production architecture in diagrams. 

 

## Reasoning 

Kafka's operational overhead (partition management, consumer group rebalancing) 

is real learning-curve cost for a 4-person team with a 20-week deadline. RabbitMQ 

gives the same event-driven decoupling pattern with a simpler mental model and 

faster local setup. The event contracts (topic names, payload schemas) are 

Page 47 of 48 



TrustNet AI — Engineering Blueprint 

broker-agnostic, so switching later is a config change, not a redesign. 

 

## Consequences 

- Faster time-to-working-integration in Phase 5. 

- Panel defense presents Kafka as the scaling target with RabbitMQ named 

  explicitly as the pragmatic substitute actually running. 

docs/adrs/0002-docker-compose-vs-kubernetes.md — same structure, decision: "Docker Compose for actual deployment, 
K8s manifests written and validated once on k3s, not run continuously." 

docs/adrs/0003-modular-monolith-vs-microservices.md — decision: "16 logical services as separate Python packages, 
deployed as 3-4 process groups for MVP; full per-service containers only once integration is stable." 

Blank template for new ADRs: 

markdown 

# ADR NNNN: <title> 

## Status: Proposed | Accepted | Superseded 

## Context 

## Decision 

## Reasoning 

## Consequences 

 

Closing Note 

This blueprint intentionally makes every 'textbook enterprise' vs. 'realistic for four students in two semesters' tradeoff 
explicit rather than silently picking one. Where the two diverge — full Kubernetes vs. Docker Compose, sixteen 
deployed microservices vs. a modular monolith staged toward that target, Kafka vs. RabbitMQ, rPPG as committed vs. 
stretch scope — the recommendation is always the same shape: design and document the enterprise-grade target 
honestly, and build the version of it that a four-person team can actually finish, measure, and defend. That combination 
is what makes both the working system and the panel defense credible. 

Page 48 of 48