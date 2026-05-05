# PLAN.md — Synthetic Persona Sandbox · Sprint Roadmap

> Methodology: 2-week sprints | Story points: Fibonacci (1, 2, 3, 5, 8, 13)
> Sprint velocity target: 40 pts/sprint
> All UI tasks must comply with `BRAND.md` before implementation begins.

---

## Milestones at a Glance

| Milestone | Sprint(s) | Deliverable |
|---|---|---|
| **M1 — Foundation** | S1 – S2 | Infrastructure up, data flowing through Kafka |
| **M2 — Persona Engine** | S3 – S4 | Segment models trained, synthetic responses generated |
| **M3 — Simulation Core** | S5 – S6 | Airflow DAGs orchestrating full simulation runs |
| **M4 — Dashboard MVP** | S7 – S8 | Marketing team can launch and view a simulation |
| **M5 — Production Hardening** | S9 – S10 | Scale, observability, security, GA release |

---

## Sprint 1 — Infrastructure & Project Skeleton
**Duration:** Weeks 1–2 | **Goal:** Everything runs locally, CI is green, team can commit.

### Tasks

| # | Task | Owner Area | Points |
|---|---|---|---|
| S1-01 | Initialize monorepo structure per `CLAUDE.md` layout | Infra | 2 |
| S1-02 | Docker Compose: Kafka + Zookeeper + PostgreSQL + Redis + Qdrant | Infra | 3 |
| S1-03 | Terraform scaffolding for cloud environments (dev/staging/prod) | Infra | 5 |
| S1-04 | CI/CD pipeline (GitHub Actions): lint, test, build on PR | DevOps | 3 |
| S1-05 | FastAPI app skeleton with health check endpoint | Backend | 2 |
| S1-06 | React + Vite + TypeScript dashboard scaffold | Frontend | 2 |
| S1-07 | Design token setup in dashboard (CSS vars from `BRAND.md`) | Frontend | 3 |
| S1-08 | Airflow local setup + `hello_world` DAG | Data Eng | 3 |
| S1-09 | PostgreSQL schema v1: users, segments, simulation_runs | Backend | 3 |
| S1-10 | `.env.example` + secrets management documentation | DevOps | 2 |
| S1-11 | Pre-commit hooks: ruff, mypy, eslint, prettier | DevOps | 2 |

**Sprint Total: 30 pts** *(lighter sprint — team onboarding overhead)*

### Definition of Done
- [ ] `docker compose up` starts all services with no errors
- [ ] `npm run dev` serves dashboard at `localhost:5173`
- [ ] FastAPI returns 200 at `/health`
- [ ] CI pipeline passes on a sample PR

---

## Sprint 2 — Kafka Ingestion Pipeline
**Duration:** Weeks 3–4 | **Goal:** Behavioral events stream end-to-end into the system.

### Tasks

| # | Task | Owner Area | Points |
|---|---|---|---|
| S2-01 | Define Avro schemas: `PageViewEvent`, `PurchaseEvent`, `SessionEvent` | Data Eng | 3 |
| S2-02 | Kafka producer: simulate navigation log stream (dev fixture) | Data Eng | 3 |
| S2-03 | Kafka consumer: write events to PostgreSQL `behavioral_events` table | Data Eng | 5 |
| S2-04 | Consumer: upsert real-time profile state in Redis | Data Eng | 5 |
| S2-05 | Schema Registry setup + compatibility checks in CI | Data Eng | 3 |
| S2-06 | Dead-letter queue (DLQ) for malformed events | Data Eng | 3 |
| S2-07 | Kafka monitoring: consumer lag dashboard in Grafana | DevOps | 3 |
| S2-08 | API endpoint: `GET /profiles/{user_id}/state` (reads from Redis) | Backend | 3 |
| S2-09 | PII anonymization layer before any event hits the DB | Backend | 5 |
| S2-10 | Integration tests: end-to-end event → Redis → API | QA | 5 |

**Sprint Total: 38 pts**

### Definition of Done
- [ ] A simulated purchase event produced to Kafka is visible in Redis within 2 seconds
- [ ] No raw PII is stored in PostgreSQL or Redis
- [ ] Consumer lag < 500ms at 1,000 events/sec load test
- [ ] DLQ captures and alerts on malformed events

---

## Sprint 3 — Segment Modeling & Data Preparation
**Duration:** Weeks 5–6 | **Goal:** Customer segments are defined and their behavioral data is ready for model training.

### Tasks

| # | Task | Owner Area | Points |
|---|---|---|---|
| S3-01 | Segment definition schema: age range, geo, category affinities, purchase history | ML | 3 |
| S3-02 | Airflow DAG: `extract_segment_data` — pulls behavioral subset per segment config | Data Eng | 5 |
| S3-03 | Feature engineering pipeline: purchase frequency, avg. basket, session depth | ML | 5 |
| S3-04 | Qdrant collection setup for persona embeddings | ML | 3 |
| S3-05 | Embedding generation: encode segment profiles into vector space | ML | 5 |
| S3-06 | API endpoints: CRUD for Segments (`/segments`) | Backend | 3 |
| S3-07 | Segment builder UI — form component (read `BRAND.md` first) | Frontend | 5 |
| S3-08 | Segment list & detail pages in dashboard | Frontend | 3 |
| S3-09 | Data validation: test feature distributions match expected segment stats | ML | 3 |
| S3-10 | Document segment modeling decisions in `ml/segment_models/README.md` | Docs | 2 |

**Sprint Total: 37 pts**

### Definition of Done
- [ ] "Gen Z, Mexico City, 18-24" segment can be defined via the UI
- [ ] `extract_segment_data` DAG runs successfully and outputs a feature matrix
- [ ] Embeddings stored in Qdrant and queryable by segment ID
- [ ] Segment pages match `BRAND.md` spec

---

## Sprint 4 — Synthetic Persona Generation (AI Core)
**Duration:** Weeks 7–8 | **Goal:** LLM-based personas can generate synthetic responses to stimuli.

### Tasks

| # | Task | Owner Area | Points |
|---|---|---|---|
| S4-01 | LLM fine-tuning pipeline: inject segment feature matrix as system context | ML | 8 |
| S4-02 | Stimulus schema: `AdCopyStimulus`, `PriceChangeStimulus`, `PromoStimulus` | ML | 3 |
| S4-03 | Persona inference service: given segment + stimulus → synthetic response | ML | 8 |
| S4-04 | Conversion score model: output probability 0–1 per stimulus | ML | 5 |
| S4-05 | GAN exploration spike: evaluate CTR-prediction GAN vs LLM approach (timeboxed 3 days) | ML | 3 |
| S4-06 | API endpoint: `POST /simulate/run` — triggers inference for a segment + stimulus | Backend | 5 |
| S4-07 | Store simulation run results in PostgreSQL | Backend | 3 |
| S4-08 | Unit tests for conversion score model (≥ 80% coverage) | QA | 3 |
| S4-09 | Evaluation harness: compare synthetic responses vs. historical holdout data | ML | 5 |

**Sprint Total: 43 pts**

### Definition of Done
- [ ] `POST /simulate/run` returns a conversion score and synthetic response text in < 5 seconds
- [ ] Conversion score on holdout validation set achieves AUC ≥ 0.72
- [ ] GAN spike documented with go/no-go recommendation
- [ ] ML functions have ≥ 80% test coverage

---

## Sprint 5 — Airflow Orchestration & Campaign Variants
**Duration:** Weeks 9–10 | **Goal:** Full simulation pipeline runs automatically; multiple ad variants compete.

### Tasks

| # | Task | Owner Area | Points |
|---|---|---|---|
| S5-01 | Airflow DAG: `run_simulation_pipeline` — segment extract → persona inference → score storage | Data Eng | 8 |
| S5-02 | DAG: `variant_competition` — runs N ad variants against same segment, ranks by score | Data Eng | 8 |
| S5-03 | Idempotency audit: all DAGs safe to re-run | Data Eng | 3 |
| S5-04 | DAG sensors: wait for Kafka consumer lag to drain before triggering simulation | Data Eng | 3 |
| S5-05 | Campaign variant schema + CRUD API (`/campaigns`, `/variants`) | Backend | 5 |
| S5-06 | Airflow DAG monitoring in Grafana (DAG duration, failure rate) | DevOps | 3 |
| S5-07 | WebSocket endpoint: stream simulation progress to dashboard in real-time | Backend | 5 |
| S5-08 | Simulation history API: `GET /simulate/runs` with filters | Backend | 3 |
| S5-09 | Integration test: full pipeline from trigger to scored result | QA | 5 |

**Sprint Total: 43 pts**

### Definition of Done
- [ ] `variant_competition` DAG correctly ranks 3 ad variants and stores results
- [ ] Re-running any DAG with same inputs produces same outputs (idempotency verified)
- [ ] WebSocket pushes progress updates to a connected client
- [ ] Full pipeline completes in < 2 minutes for a single segment

---

## Sprint 6 — Real-Time Simulation Engine Polish
**Duration:** Weeks 11–12 | **Goal:** Simulation is robust, observable, and handles concurrency.

### Tasks

| # | Task | Owner Area | Points |
|---|---|---|---|
| S6-01 | Concurrency: run up to 5 simultaneous simulation jobs without degradation | Backend | 5 |
| S6-02 | Redis job queue for simulation requests (Celery or ARQ) | Backend | 5 |
| S6-03 | Rate limiting on `POST /simulate/run` (per org, per minute) | Backend | 3 |
| S6-04 | Prometheus metrics: simulation latency, queue depth, error rate | DevOps | 3 |
| S6-05 | Alert rules: simulation failure rate > 5% → PagerDuty | DevOps | 2 |
| S6-06 | Retry logic for LLM inference failures (exponential backoff) | ML | 3 |
| S6-07 | Persona drift detection: flag segments with stale data (> 7 days) | ML | 5 |
| S6-08 | Load test: 20 concurrent simulation runs @ p99 < 10s | QA | 5 |
| S6-09 | Error taxonomy documentation for simulation failures | Docs | 2 |
| S6-10 | Smoke test suite for critical simulation paths | QA | 3 |

**Sprint Total: 36 pts**

### Definition of Done
- [ ] 20 concurrent simulations complete with p99 latency < 10 seconds
- [ ] Failed simulations auto-retry up to 3 times before marking as failed
- [ ] Grafana dashboard shows live queue depth and error rate
- [ ] Stale segment alert fires correctly in staging

---

## Sprint 7 — Dashboard Core: Campaign Launcher
**Duration:** Weeks 13–14 | **Goal:** Marketing team can launch a simulation from the UI and see live progress.

> ⚠️ All components this sprint require `BRAND.md` review before implementation.

### Tasks

| # | Task | Owner Area | Points |
|---|---|---|---|
| S7-01 | Campaign Launcher page — multi-step form: segment → stimulus → variants | Frontend | 8 |
| S7-02 | Stimulus builder: rich text editor for ad copy, image upload, price input | Frontend | 5 |
| S7-03 | WebSocket hook `useSimulationProgress` — live status & progress bar | Frontend | 5 |
| S7-04 | Simulation "loading" state — animated persona thinking indicator (per `BRAND.md`) | Frontend | 3 |
| S7-05 | Simulation results page: conversion score per variant, ranked leaderboard | Frontend | 5 |
| S7-06 | Synthetic response viewer: show what each persona "said" about the ad | Frontend | 5 |
| S7-07 | Navigation and routing (React Router v6) | Frontend | 2 |
| S7-08 | Zustand store: campaigns, simulation state, results | Frontend | 3 |
| S7-09 | Responsive layout for all new pages (desktop + tablet) | Frontend | 3 |
| S7-10 | Accessibility audit: WCAG 2.1 AA on Launcher and Results pages | Frontend | 2 |

**Sprint Total: 41 pts**

### Definition of Done
- [ ] A marketer can go from "create campaign" to "see results" without leaving the browser
- [ ] Conversion scores update in real-time via WebSocket
- [ ] All pages pass `BRAND.md` design review
- [ ] WCAG 2.1 AA compliance on core pages

---

## Sprint 8 — Dashboard: Analytics & Persona Explorer
**Duration:** Weeks 15–16 | **Goal:** Marketers can explore segment profiles and historical simulation data.

> ⚠️ All components this sprint require `BRAND.md` review before implementation.

### Tasks

| # | Task | Owner Area | Points |
|---|---|---|---|
| S8-01 | Conversion Prediction dashboard: chart showing score over time per segment | Frontend | 5 |
| S8-02 | Segment Explorer: visualize persona profile (affinities, behavior heatmap) | Frontend | 8 |
| S8-03 | Simulation history table with filters (date, segment, score range) | Frontend | 5 |
| S8-04 | Variant comparison view: side-by-side A/B results | Frontend | 5 |
| S8-05 | Export: download simulation results as CSV | Frontend | 2 |
| S8-06 | Summary stats widgets: avg conversion, top segment, best variant | Frontend | 3 |
| S8-07 | Charting library integration (Recharts or Visx — per `BRAND.md` spec) | Frontend | 3 |
| S8-08 | Dark mode implementation across all dashboard pages | Frontend | 5 |
| S8-09 | Storybook: document all new components | Frontend | 3 |
| S8-10 | E2E tests: Playwright scripts for Launcher → Results → History flow | QA | 5 |

**Sprint Total: 44 pts**

### Definition of Done
- [ ] Marketing team UAT sign-off on dashboard flows
- [ ] Dark mode works on all pages without visual regressions
- [ ] Playwright E2E suite passes in CI
- [ ] Storybook documents all components introduced in S7–S8

---

## Sprint 9 — Security, Auth & Multi-Tenancy
**Duration:** Weeks 17–18 | **Goal:** Platform is secure and supports multiple client organizations.

### Tasks

| # | Task | Owner Area | Points |
|---|---|---|---|
| S9-01 | Authentication: Auth0 / Clerk integration (JWT) | Backend | 5 |
| S9-02 | RBAC: roles — `admin`, `marketer`, `analyst`, `viewer` | Backend | 5 |
| S9-03 | Multi-tenancy: org-scoped data isolation at DB level (row-level security) | Backend | 8 |
| S9-04 | API key management for programmatic access | Backend | 3 |
| S9-05 | Login, invite, and org-switcher UI | Frontend | 5 |
| S9-06 | Audit log: record who triggered which simulation and when | Backend | 3 |
| S9-07 | Penetration test scope definition + OWASP Top 10 checklist | Security | 3 |
| S9-08 | Secrets rotation automation (K8s + Vault or AWS Secrets Manager) | DevOps | 5 |
| S9-09 | GDPR compliance review: right to deletion cascade | Backend | 3 |
| S9-10 | Security documentation for SOC 2 readiness | Docs | 2 |

**Sprint Total: 42 pts**

### Definition of Done
- [ ] An unauthenticated request to any API endpoint returns 401
- [ ] Org A cannot read Org B's simulation data (verified by integration test)
- [ ] Audit log captures all simulation triggers
- [ ] GDPR deletion cascade tested end-to-end

---

## Sprint 10 — Production Hardening & GA Release
**Duration:** Weeks 19–20 | **Goal:** Platform is production-ready, observable, documented, and released.

### Tasks

| # | Task | Owner Area | Points |
|---|---|---|---|
| S10-01 | Kubernetes manifests for all services (HPA, resource limits, liveness probes) | DevOps | 8 |
| S10-02 | Blue/green deployment pipeline for API and dashboard | DevOps | 5 |
| S10-03 | Full observability stack: Prometheus + Grafana + Loki + Tempo | DevOps | 5 |
| S10-04 | SLO definition and burn-rate alerts (API p99 < 2s, simulation success > 98%) | DevOps | 3 |
| S10-05 | Database backup automation + tested restore procedure | DevOps | 3 |
| S10-06 | Performance tuning: Qdrant query optimization, Redis TTL strategy | Backend | 5 |
| S10-07 | Full regression test run on staging environment | QA | 5 |
| S10-08 | User documentation: "How to run your first simulation" guide | Docs | 3 |
| S10-09 | API reference documentation (auto-generated from FastAPI + reviewed) | Docs | 2 |
| S10-10 | Go/No-Go checklist review and GA sign-off | All | 2 |

**Sprint Total: 41 pts**

### Definition of Done
- [ ] All services running on Kubernetes with HPA configured
- [ ] Zero-downtime deployment demonstrated in staging
- [ ] SLO dashboards live and alerting tested
- [ ] Full user documentation published
- [ ] Go/No-Go checklist signed off by all team leads

---

## Post-GA Backlog (Future Sprints)

> Items identified but not yet scheduled. Prioritize in sprint planning as capacity allows.

- **GAN implementation** — replace/augment LLM persona with purpose-trained GAN for CTR prediction
- **Multi-language support** — personas and stimulus in EN, ES, PT, FR
- **Integrations** — Meta Ads API, Google Ads API for direct campaign import
- **Persona aging** — automatic drift & retraining when segment behavior shifts significantly
- **Budget optimizer** — given a budget and N variants, recommend optimal allocation
- **Mobile dashboard** — responsive breakpoints for phones
- **Slack / Teams bot** — trigger simulations and receive results via chat

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM inference latency too high | Medium | High | Cache frequent segment+stimulus combos in Redis; explore smaller fine-tuned models |
| Synthetic responses don't correlate with real outcomes | Medium | Critical | Maintain holdout validation set; require AUC ≥ 0.72 gate before S5 |
| Kafka lag under high load | Low | High | Horizontal consumer scaling; consumer group monitoring from S2 |
| PII leakage into model training | Low | Critical | Anonymization layer enforced in S2; regular data audits |
| Scope creep on dashboard | High | Medium | Strict `BRAND.md` + Figma-first workflow; no unplanned UI features mid-sprint |
