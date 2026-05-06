# CLAUDE.md — Synthetic Persona Sandbox

> This file is the source of truth for Claude Code when working on this project.
> Read it fully before making any change, generating any file, or running any command.

---

## Project Overview

**The Synthetic Persona Sandbox** is a marketing simulation platform that creates AI-powered digital twins of customer segments. It allows marketing teams to test campaigns against synthetic personas derived from real behavioral data — before spending a single dollar on ads.

**Core value proposition:** Replace slow, expensive A/B testing with real-time campaign simulation powered by streaming data, LLMs, and generative models.

---

## Repository Structure

```
synthetic-persona-sandbox/
├── ingestion/                  # Kafka consumers & producers
│   ├── consumers/
│   ├── producers/
│   └── schemas/                # Avro/Protobuf schemas
├── orchestration/              # Airflow DAGs
│   ├── dags/
│   └── plugins/
├── ml/                         # ML & AI pipeline
│   ├── synthetic_data/         # GAN / LLM fine-tuning
│   ├── segment_models/         # Per-segment persona models
│   └── evaluation/             # Scoring & validation
├── api/                        # FastAPI backend
│   ├── routers/
│   ├── models/
│   └── services/
├── dashboard/                  # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── store/
│   └── public/
├── infra/                      # Terraform / Docker / K8s
│   ├── terraform/
│   ├── docker/
│   └── k8s/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── simulation/
├── BRAND.md                    # ← UI/UX design decisions (see below)
├── CLAUDE.md                   # ← This file
└── PLAN.md                     # ← Sprint roadmap
```

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Streaming | Apache Kafka | Navigation & purchase event ingestion |
| Orchestration | Apache Airflow | DAG-based simulation pipelines |
| Synthetic AI | GANs + LLMs (fine-tuned) | Persona response generation |
| Backend API | FastAPI (Python 3.11+) | REST + WebSocket for real-time updates |
| Frontend | React 18 + TypeScript + Vite | Dashboard UI |
| State Management | Zustand | Frontend store |
| Database | PostgreSQL + Redis | Persistent store + caching |
| Vector Store | Qdrant | Persona embeddings |
| Infrastructure | Docker + Kubernetes + Terraform | Cloud-agnostic |
| Monitoring | Prometheus + Grafana | Observability |

---

## UI Decisions

> **All UI, design, and branding decisions are governed by [`BRAND.md`](./BRAND.md).**
>
> Before generating any component, page, style, color, typography choice, icon set,
> layout, or copy — read `BRAND.md` first. Do not deviate from it.

Key rules for UI work:
- Never hardcode colors or fonts — always use the design tokens defined in `BRAND.md`
- Component naming conventions follow the patterns in `BRAND.md`
- All dashboard components must support both light and dark mode as specified in `BRAND.md`
- Iconography, illustration style, and data visualization palettes are defined in `BRAND.md`

---

## Development Conventions

### Python
- Python 3.11+ required
- Use `uv` for dependency management (`uv add`, `uv run`)
- Type hints are mandatory on all functions
- Docstrings follow Google style
- Formatter: `ruff format` | Linter: `ruff check`
- Tests: `pytest` with `pytest-asyncio` for async code

### TypeScript / React
- Strict TypeScript (`"strict": true` in tsconfig)
- Functional components only — no class components
- Custom hooks live in `src/hooks/`, prefixed with `use`
- All API calls go through the centralized `src/services/api.ts`
- No inline styles — use CSS Modules or Tailwind (per `BRAND.md`)

### Git
- Branch naming: `feat/`, `fix/`, `chore/`, `docs/`
- Commits follow Conventional Commits spec (`feat: add persona scoring API`)
- PRs require passing CI and one peer review

### Environment Variables
- Never hardcode secrets — use `.env` files locally, K8s secrets in prod
- `.env.example` must be kept up to date at all times

---

## Key Concepts & Domain Language

| Term | Definition |
|---|---|
| **Persona** | An AI-powered digital twin representing a customer segment |
| **Segment** | A defined subset of users (e.g., "Gen Z, Madrid, 18-24") |
| **Simulation Run** | A campaign variant tested against one or more personas |
| **Stimulus** | The input to a persona: ad copy, price change, image, promo |
| **Synthetic Response** | The persona's predicted reaction to a stimulus |
| **Conversion Score** | Probability (0–1) that a segment converts given a stimulus |
| **DAG** | Airflow Directed Acyclic Graph — defines a simulation pipeline |
| **Profile State** | Real-time user behavior state maintained via Kafka streams |

---

## Architecture Constraints

1. **Data privacy first** — Raw PII must never reach the LLM. All persona training data is anonymized and aggregated before injection.
2. **Kafka is the system of record** — All behavioral events flow through Kafka. Do not bypass it with direct DB writes for event data.
3. **Airflow owns scheduling** — Do not build custom cron jobs. All batch/simulation jobs are Airflow DAGs.
4. **Stateless API** — The FastAPI backend is stateless. Session state lives in Redis. Long-running simulation state lives in PostgreSQL.
5. **Idempotent DAGs** — Every Airflow DAG must be safe to re-run without side effects.

---

## Running Locally

```bash
# 1. Start infrastructure
docker compose up -d kafka zookeeper postgres redis qdrant

# 2. Install Python deps
uv sync

# 3. Run Airflow locally
uv run airflow standalone

# 4. Start API
uv run uvicorn api.main:app --reload --port 8000

# 5. Start dashboard
cd dashboard && npm install && npm run dev
```

---

## Testing

```bash
# Unit tests
uv run pytest tests/unit/

# Integration tests (requires docker compose up)
uv run pytest tests/integration/

# Simulation smoke test
uv run pytest tests/simulation/ -k "smoke"
```

---

## Common Claude Code Tasks

When asked to:

- **Add a new persona segment** → Start in `ml/segment_models/`, add corresponding Kafka schema in `ingestion/schemas/`, update the FastAPI router in `api/routers/personas.py`
- **Build a new dashboard page** → Read `BRAND.md` first, create page in `dashboard/src/pages/`, add route in `dashboard/src/App.tsx`
- **Add a new Airflow DAG** → Place in `orchestration/dags/`, follow existing DAG naming pattern, ensure idempotency
- **Modify synthetic data generation** → Work in `ml/synthetic_data/`, document model changes in that directory's `README.md`
- **Add an API endpoint** → Add router in `api/routers/`, add Pydantic models in `api/models/`, write integration test

---

## Do Not

- Do not modify `BRAND.md` — it is maintained by the design team
- Do not commit directly to `main`
- Do not use `any` type in TypeScript
- Do not write raw SQL outside of the designated `api/services/db.py` layer
- Do not expose Kafka internals through the public API
- Do not skip writing tests for ML scoring functions — they are business-critical

---

## Estado actual del proyecto

```
Sprint 1 — Infrastructure & Project Skeleton   [x] Completado (2026-05-05)
Sprint 2 — Kafka Ingestion Pipeline            [x] Completado (2026-05-05)
Sprint 3 — Segment Modeling & Data Preparation [x] Completado (2026-05-05)
Sprint 4 — Synthetic Persona Generation        [x] Completado (2026-05-05)
Sprint 5 — Airflow Orchestration               [x] Completado (2026-05-05)
Sprint 6 — Real-Time Simulation Engine Polish  [x] Completado (2026-05-06)
Sprint 7 — Dashboard Core: Campaign Launcher   [x] Completado (2026-05-06)
Sprint 8 — Dashboard: Analytics & Persona Exp  [x] Completado (2026-05-06)
Sprint 9 — Security, Auth & Multi-Tenancy      [x] Completado (2026-05-06)
Sprint 10 — Production Hardening & GA Release  [x] Completado (2026-05-06)
```

Actualiza esta sección al final de cada sesión de trabajo.
