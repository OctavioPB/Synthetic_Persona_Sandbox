# Synthetic Persona Sandbox

> **AI-powered marketing simulation platform.** Create digital twins of your customer segments and test campaigns against them — before spending a single dollar on ads.

---

## What is this?

The Synthetic Persona Sandbox lets marketing teams simulate how a specific customer segment would respond to an ad, a price change, or a promotional offer. It builds synthetic personas from behavioral data and uses LLMs (Claude) to generate realistic, segment-specific responses. Results include a **conversion score**, sentiment analysis, and the persona's verbatim reaction.

**Core loop:**

```
Define segment → Build ad variant → Launch simulation → Read conversion score
```

Instead of waiting weeks for A/B test results, a marketer can run 10 variants against 5 segments in under 5 minutes, identify the weakest performers, and go to production with only the top candidates.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  STREAMING LAYER                                                    │
│  Kafka + Schema Registry ← behavioral events (page views, purchases) │
│  Consumer → PostgreSQL (events) + Redis (profile state)             │
├─────────────────────────────────────────────────────────────────────┤
│  ORCHESTRATION LAYER                                                │
│  Airflow DAGs: extract_segment_data · run_simulation_pipeline       │
│                variant_competition · drift_check                    │
├─────────────────────────────────────────────────────────────────────┤
│  ML / AI LAYER                                                      │
│  Segment embeddings (sentence-transformers → Qdrant)                │
│  Persona inference (Claude claude-sonnet-4-6 via Anthropic API)     │
│  Conversion scorer (logistic model on LLM output features)          │
├─────────────────────────────────────────────────────────────────────┤
│  API LAYER                                                          │
│  FastAPI (async) · ARQ job queue · WebSocket progress stream        │
│  JWT + API key auth · RBAC (viewer/analyst/marketer/admin)          │
│  Multi-tenant data isolation by org_id                              │
├─────────────────────────────────────────────────────────────────────┤
│  DASHBOARD                                                          │
│  React 18 + TypeScript + Vite · Zustand · Recharts                  │
│  Campaign Launcher · Analytics · Segment Explorer · Dark mode       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Streaming** | Apache Kafka + Confluent Schema Registry | 7.6.1 |
| **Orchestration** | Apache Airflow | 2.9+ |
| **Vector store** | Qdrant | 1.9.7 |
| **Database** | PostgreSQL | 16 |
| **Cache / Queue** | Redis | 7.2 |
| **Backend API** | FastAPI + Uvicorn | 0.111+ |
| **Job queue** | ARQ (async Redis queue) | 0.26+ |
| **AI inference** | Anthropic Claude (`claude-sonnet-4-6`) | anthropic 0.40+ |
| **Embeddings** | `all-MiniLM-L6-v2` via sentence-transformers | 3.0+ |
| **Auth** | PyJWT (HS256 dev / RS256 prod) | 2.8+ |
| **Frontend** | React 18 + TypeScript + Vite | Node 20 |
| **State management** | Zustand | 4+ |
| **Charts** | Recharts | 2+ |
| **Observability** | Prometheus + Grafana + Loki | — |
| **Infrastructure** | Docker Compose (dev) · Kubernetes (prod) | — |
| **Package manager (Python)** | uv | latest |
| **Linter / formatter** | Ruff + Mypy | 0.4+ / 1.10+ |

---

## Project Structure

```
synthetic-persona-sandbox/
│
├── api/                          # FastAPI backend
│   ├── auth/
│   │   ├── dependencies.py       # get_current_user, require() factory
│   │   ├── jwt_handler.py        # encode_token, decode_token, TokenClaims
│   │   └── rbac.py               # Permission enum, ROLE_PERMISSIONS
│   ├── models/
│   │   ├── campaign.py           # CampaignORM, CampaignVariantORM
│   │   ├── org.py                # OrganizationORM, OrgMemberORM, ApiKeyORM, AuditEventORM
│   │   ├── segment.py            # SegmentORM + Pydantic schemas
│   │   └── simulation.py         # SimulationRunORM + Pydantic schemas
│   ├── routers/
│   │   ├── auth.py               # /auth — dev token, API key CRUD
│   │   ├── campaigns.py          # /campaigns — campaign + variant CRUD
│   │   ├── health.py             # /health — liveness probe
│   │   ├── org.py                # /org — members, audit log, GDPR deletion
│   │   ├── profiles.py           # /profiles — real-time user state (Redis)
│   │   ├── segments.py           # /segments — segment CRUD
│   │   ├── simulations.py        # /simulate — async + sync runs
│   │   └── ws.py                 # /ws — WebSocket progress stream
│   ├── services/
│   │   ├── audit.py              # log_event() — fire-and-forget audit writes
│   │   ├── cache.py              # Redis cache-aside layer (TTL strategy)
│   │   ├── db.py                 # SQLAlchemy async session, Base
│   │   ├── metrics.py            # Prometheus counters and histograms
│   │   ├── queue.py              # ARQ pool singleton + QueueDep
│   │   └── rate_limiter.py       # Sliding-window rate limiter (10 req/min/org)
│   ├── main.py                   # FastAPI app, middleware, router registration
│   └── worker.py                 # ARQ worker entry point
│
├── dashboard/                    # React + TypeScript frontend
│   ├── src/
│   │   ├── components/           # Nav, Footer, SegmentCard, charts, etc.
│   │   ├── hooks/
│   │   │   ├── useSimulationProgress.ts  # WebSocket hook
│   │   │   └── useTheme.ts               # Dark mode hook
│   │   ├── pages/
│   │   │   ├── AnalyticsPage.tsx         # Charts, history table, variant compare
│   │   │   ├── CampaignLauncherPage.tsx  # 3-step campaign wizard
│   │   │   ├── DashboardPage.tsx         # Overview KPIs
│   │   │   ├── LoginPage.tsx             # Dev login / IdP redirect
│   │   │   ├── SegmentBuilderPage.tsx    # Segment creation form
│   │   │   ├── SegmentDetailPage.tsx     # Persona Explorer
│   │   │   ├── SegmentsPage.tsx          # Segment list
│   │   │   └── SimulationResultsPage.tsx # Ranked leaderboard
│   │   ├── services/
│   │   │   └── api.ts            # Centralized API client
│   │   ├── store/
│   │   │   ├── authStore.ts      # JWT token + user, localStorage persistence
│   │   │   └── campaignStore.ts  # Campaign wizard state + results
│   │   └── styles/
│   │       └── tokens.css        # Design tokens (light + dark mode)
│   ├── tests/e2e/                # Playwright end-to-end tests
│   ├── .storybook/               # Storybook config
│   └── vite.config.ts
│
├── ingestion/                    # Kafka consumers and producers
│   ├── consumers/                # Write events to PostgreSQL + Redis
│   ├── producers/                # Simulate behavioral event streams
│   ├── anonymizer.py             # PII anonymization before storage
│   └── schemas/                  # Avro schemas (.avsc)
│
├── orchestration/
│   └── dags/
│       ├── extract_segment_data.py       # Pull + embed segment behavioral data
│       ├── run_simulation_pipeline.py    # Segment → inference → store results
│       ├── variant_competition.py        # Run N variants, rank by score
│       └── drift_check.py               # Flag stale segments (> 7 days)
│
├── ml/
│   ├── segment_models/
│   │   ├── embedding_service.py  # sentence-transformers → Qdrant upsert
│   │   ├── feature_engineering.py
│   │   ├── qdrant_setup.py       # Collection management
│   │   └── segment_schema.py     # Pydantic segment definition schema
│   ├── synthetic_data/
│   │   ├── claude_client.py      # Anthropic client with disk cache + retry
│   │   ├── conversion_scorer.py  # 0–1 score from LLM output features
│   │   ├── persona_context_builder.py  # Build system prompt from segment
│   │   ├── persona_inference.py  # Claude inference → PersonaResponse
│   │   └── stimulus_schema.py    # AdCopyStimulus | PriceChangeStimulus | PromoStimulus
│   └── evaluation/
│       ├── drift_detector.py     # Detect behavioral drift per segment
│       └── holdout_evaluator.py  # AUC evaluation against holdout set
│
├── migrations/                   # PostgreSQL migration SQL files (idempotent)
│   ├── 001_initial_schema.sql
│   ├── 002_behavioral_events.sql
│   ├── 003_campaigns_and_sim_columns.sql
│   └── 004_security_and_tenancy.sql
│
├── tests/
│   ├── unit/                     # Fast, no external dependencies
│   ├── integration/              # Require PostgreSQL + Redis
│   │   ├── test_pipeline.py      # Kafka → Redis → API flow
│   │   ├── test_simulation_pipeline.py
│   │   └── test_regression.py    # Full regression suite (Sprint 10)
│   ├── simulation/               # Simulation smoke tests
│   └── load/
│       └── locustfile.py         # Load test: 20 concurrent simulations
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile.api        # Python 3.11-slim + uv
│   │   ├── Dockerfile.dashboard  # Node 20 builder → nginx:1.27-alpine
│   │   ├── nginx.conf
│   │   ├── prometheus.yml
│   │   └── grafana/              # Pre-provisioned dashboards
│   ├── k8s/
│   │   ├── api-deployment.yaml   # HPA, readOnlyRootFilesystem, blue/green slot
│   │   ├── dashboard-deployment.yaml
│   │   ├── worker-deployment.yaml
│   │   ├── hpa.yaml              # HorizontalPodAutoscaler v2
│   │   ├── ingress.yaml          # TLS + cert-manager + security headers
│   │   ├── configmap.yaml
│   │   ├── secrets-template.yaml
│   │   ├── monitoring/           # ServiceMonitor, PrometheusRule SLO alerts, Loki
│   │   └── backup/               # pg_dump CronJob → S3
│   └── terraform/                # Cloud environment definitions (dev/staging/prod)
│
├── docs/
│   ├── api/README.md             # Full API endpoint reference
│   ├── guides/first_simulation.md
│   ├── release/ga_checklist.md   # Go/No-Go checklist
│   └── security/
│       ├── owasp_checklist.md    # OWASP Top 10 mitigations
│       └── soc2_controls.md      # SOC 2 Type II control documentation
│
├── .github/workflows/
│   ├── ci.yml                    # Lint, type-check, unit + integration tests
│   └── deploy.yml                # Build → staging → integration → production (blue/green)
│
├── docker-compose.yml            # Full local stack
├── pyproject.toml                # Python dependencies + tooling config
├── BRAND.md                      # UI/UX design tokens and decisions
├── CLAUDE.md                     # Claude Code session instructions
└── PLAN.md                       # Sprint roadmap
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| **Docker Desktop** | 24+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| **Python** | 3.11+ | [python.org](https://www.python.org/downloads/) |
| **uv** | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Node.js** | 20 LTS | [nodejs.org](https://nodejs.org/) |
| **Anthropic API key** | — | [console.anthropic.com](https://console.anthropic.com/) |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/opb/synthetic-persona-sandbox.git
cd synthetic-persona-sandbox
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

```dotenv
# ── Required ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...              # Your Anthropic API key

# ── Database ──────────────────────────────────────────────────────────────────
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=synthetic_persona
POSTGRES_USER=spb_user
POSTGRES_PASSWORD=changeme               # Change in production

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_REQUIRED=false                      # Set to "true" in production
AUTH_MODE=dev                            # Set to "production" in production
JWT_SECRET=dev-secret-change-in-prod     # Min 32 chars, high-entropy in production

# ── Application ───────────────────────────────────────────────────────────────
ENV=development
LOG_LEVEL=DEBUG

# ── Qdrant ────────────────────────────────────────────────────────────────────
QDRANT_HOST=localhost
QDRANT_PORT=6333

# ── Kafka ─────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### 3. Install Python dependencies

```bash
uv sync --extra dev
```

### 4. Install dashboard dependencies

```bash
cd dashboard && npm install && cd ..
```

---

## Running Locally

### Option A — Full Docker Compose stack (recommended)

Starts all infrastructure services (Kafka, PostgreSQL, Redis, Qdrant, Prometheus, Grafana):

```bash
docker compose up -d
```

Verify services are healthy:

```bash
docker compose ps
```

Expected output — all services should be `healthy` or `running`:

```
spb-postgres         healthy
spb-redis            healthy
spb-kafka            running
spb-schema-registry  running
spb-qdrant           running
spb-prometheus       running
spb-grafana          running
```

### Option B — Infrastructure only + local API

If you prefer to run the API outside Docker (faster iteration):

```bash
# Start only infrastructure services
docker compose up -d postgres redis qdrant kafka schema-registry

# Start API (reloads on file changes)
uv run uvicorn api.main:app --reload --port 8000

# Start ARQ worker (separate terminal)
uv run python -m api.worker

# Start dashboard dev server (separate terminal)
cd dashboard && npm run dev
```

### Access the services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Dashboard** | http://localhost:5173 | — |
| **API (Swagger UI)** | http://localhost:8000/docs | — |
| **API (ReDoc)** | http://localhost:8000/redoc | — |
| **Grafana** | http://localhost:3000 | admin / changeme |
| **Prometheus** | http://localhost:9090 | — |
| **Qdrant UI** | http://localhost:6333/dashboard | — |
| **Airflow** | http://localhost:8080 | admin / admin |

---

## Database Migrations

Migrations are plain SQL files in `migrations/` and run automatically when PostgreSQL starts (via `docker-entrypoint-initdb.d`). To apply them manually:

```bash
# Apply all migrations in order
for f in migrations/*.sql; do
  echo "Applying $f..."
  PGPASSWORD=changeme psql -h localhost -U spb_user -d synthetic_persona -f "$f"
done
```

Migration history:

| File | What it creates |
|------|----------------|
| `001_initial_schema.sql` | `segments`, `simulation_runs` |
| `002_behavioral_events.sql` | `behavioral_events`, `user_profiles` |
| `003_campaigns_and_sim_columns.sql` | `campaigns`, `campaign_variants`, scoring columns |
| `004_security_and_tenancy.sql` | `organizations`, `org_members`, `api_keys`, `audit_events`; adds `org_id` to all tenant tables |

All migrations are **idempotent** — safe to re-run.

---

## Airflow Setup

```bash
# Install Airflow dependencies
uv sync --extra airflow

# Initialize the Airflow database and create admin user
uv run airflow db migrate
uv run airflow users create \
  --username admin --password admin \
  --firstname Admin --lastname User \
  --role Admin --email admin@localhost

# Start Airflow (scheduler + webserver in standalone mode)
uv run airflow standalone
```

Available DAGs:

| DAG | Schedule | Description |
|-----|----------|-------------|
| `extract_segment_data` | Manual / daily | Pull behavioral data, compute embedding, store in Qdrant |
| `run_simulation_pipeline` | Manual | Segment → persona inference → score storage |
| `variant_competition` | Manual | Run N ad variants against same segment, rank by score |
| `drift_check` | Daily 06:00 UTC | Flag segments with data older than 7 days |

---

## Authentication

### Development (default)

With `AUTH_REQUIRED=false` (default), all requests are automatically authenticated as `dev-guest` with `admin` role. No token needed.

### Getting a dev JWT

With `AUTH_MODE=dev`, you can issue a token manually:

```bash
curl -s -X POST http://localhost:8000/auth/dev-token \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "role": "marketer"}' \
  | jq .access_token
```

Use the token in subsequent requests:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/segments
```

### API Keys

Create a long-lived API key (requires admin role):

```bash
curl -s -X POST http://localhost:8000/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "My Integration Key", "role": "marketer", "expires_days": 90}'
```

The `raw_key` field in the response (format: `spb_...`) is shown **once only**. Use it via:

```bash
curl -H "X-API-Key: spb_..." http://localhost:8000/segments
```

### RBAC roles

| Role | Capabilities |
|------|-------------|
| `viewer` | Read segments, campaigns, simulation results |
| `analyst` | `viewer` + read audit log |
| `marketer` | `analyst` + create/edit segments, campaigns, run simulations |
| `admin` | All permissions + manage members, API keys, GDPR deletion |

---

## Running Your First Simulation

### Via the dashboard

1. Open http://localhost:5173
2. Click **Segments → New Segment**, define an audience (age, geo, affinities)
3. Click **Campaigns → New Campaign**, select your segment
4. Add two variants with different ad copy
5. Click **Launch Simulation** — watch the real-time progress bars
6. Review conversion scores in the results leaderboard

### Via the API

```bash
# 1. Create a segment
SEGMENT=$(curl -s -X POST http://localhost:8000/segments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gen Z Madrid",
    "description": "Urban 18-24, high digital engagement",
    "definition": {
      "age_range": {"min_age": 18, "max_age": 24},
      "geo": {"city": "Madrid", "country": "Spain"},
      "category_affinities": ["Fashion", "Electronics"],
      "purchase_history_days": 90
    }
  }')
SEGMENT_ID=$(echo $SEGMENT | jq -r .id)

# 2. Launch a simulation
curl -s -X POST http://localhost:8000/simulate/run \
  -H "Content-Type: application/json" \
  -d "{
    \"segment_id\": \"$SEGMENT_ID\",
    \"stimulus\": {
      \"type\": \"ad_copy\",
      \"headline\": \"Summer Drop — Limited Edition\",
      \"body_copy\": \"New collection just landed. Move fast.\",
      \"cta\": \"Shop Now\"
    }
  }" | jq '{id, status}'
```

---

## Testing

```bash
# Unit tests (no external services needed)
uv run pytest tests/unit/ -v

# Integration regression suite (requires Docker Compose stack running)
uv run pytest tests/integration/test_regression.py -v --tb=short

# Full integration suite
uv run pytest tests/integration/ -v

# Simulation smoke tests
uv run pytest tests/simulation/ -k smoke -v

# Load test (20 concurrent users)
uv run locust -f tests/load/locustfile.py --headless \
  -u 20 -r 5 --run-time 60s --host http://localhost:8000
```

### Frontend tests

```bash
cd dashboard

# TypeScript type check
npm run type-check

# ESLint
npm run lint

# Storybook (component development)
npm run storybook

# Playwright E2E tests (requires dev server running)
npm run dev &
npm run e2e
```

---

## Building for Production

### Docker images

```bash
# API image
docker build -f infra/docker/Dockerfile.api -t spb-api:latest .

# Dashboard image (multi-stage: build → nginx)
docker build -f infra/docker/Dockerfile.dashboard -t spb-dashboard:latest .
```

### Environment variables for production

| Variable | Required | Notes |
|----------|----------|-------|
| `ANTHROPIC_API_KEY` | Yes | Production key with appropriate rate limits |
| `JWT_SECRET` | Yes | Min 32 chars, cryptographically random |
| `POSTGRES_PASSWORD` | Yes | Strong password, not `changeme` |
| `AUTH_REQUIRED` | Yes | Set to `true` |
| `AUTH_MODE` | Yes | Set to `production` |
| `ENV` | Yes | Set to `production` |

---

## Deployment (Kubernetes)

Apply the manifests in order:

```bash
# 1. Namespace + ConfigMap + Secrets
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/configmap.yaml
# Create the secret from your vault / CI secrets (never commit real values):
kubectl create secret generic spb-secrets -n spb \
  --from-literal=ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  --from-literal=POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
  --from-literal=JWT_SECRET=$JWT_SECRET

# 2. Application deployments
kubectl apply -f infra/k8s/api-deployment.yaml
kubectl apply -f infra/k8s/worker-deployment.yaml
kubectl apply -f infra/k8s/dashboard-deployment.yaml

# 3. Autoscaling
kubectl apply -f infra/k8s/hpa.yaml

# 4. Ingress (requires cert-manager and nginx-ingress-controller)
kubectl apply -f infra/k8s/ingress.yaml

# 5. Monitoring
kubectl apply -f infra/k8s/monitoring/

# 6. Backup
kubectl apply -f infra/k8s/backup/pg-backup-cronjob.yaml
```

The CI/CD pipeline (`.github/workflows/deploy.yml`) automates this:
- **Push to `main`** → builds images, deploys to staging, runs integration tests
- **Push a `v*.*.*` tag** → deploys to production after manual approval gate

---

## Key Design Decisions

### LLM is not in the hot path during inference
The LLM (Claude) is called during simulation jobs, which run asynchronously via the ARQ job queue. The API returns 202 immediately; clients poll or stream via WebSocket. This decouples API latency from LLM latency (which can be 3–8s).

### PII never reaches the LLM
The segment definition fed to the persona inference service contains only aggregated, anonymized behavioral features — no individual user records, emails, or identifiers. This is enforced by the anonymization layer in `ingestion/anonymizer.py`.

### Multi-tenancy via application-level org_id filtering
Every query in every router filters by `claims.org_id`. There is no row-level security at the database level (PostgreSQL RLS is a future option). This means correct behavior depends entirely on the auth middleware being active — which is why `AUTH_REQUIRED=true` is enforced in production via the K8s ConfigMap.

### Redis cache-aside for completed runs
Completed simulation runs are immutable. `GET /simulate/runs/{id}` checks Redis first (24h TTL) before hitting PostgreSQL. Pending runs have a 30s TTL and are always re-fetched. This reduces DB load during real-time polling from multiple WebSocket clients.

### Rate limiting per org, not per IP
The sliding-window rate limiter keys on `org_id` (10 simulation requests/minute). IP-based limits are not used because all production traffic arrives through a load balancer with the same IP pool.

---

## API Overview

| Resource | Endpoints |
|----------|-----------|
| **Auth** | `POST /auth/dev-token` · `POST/GET/DELETE /auth/keys` |
| **Org** | `GET /org` · `GET/POST/DELETE /org/members` · `GET /org/audit` · `DELETE /org/data` |
| **Segments** | `POST/GET /segments` · `GET/PUT/DELETE /segments/{id}` |
| **Simulations** | `POST /simulate/run` (async) · `POST /simulate/run/sync` · `GET /simulate/runs` · `GET /simulate/runs/{id}` |
| **Campaigns** | `POST/GET /campaigns` · `GET/PUT/DELETE /campaigns/{id}` · `POST/GET/DELETE /campaigns/{id}/variants/{vid}` |
| **Profiles** | `GET /profiles/{user_id}/state` |
| **WebSocket** | `ws://.../ws/simulations/{run_id}` |
| **Health** | `GET /health` · `GET /metrics` |

Full reference: [`docs/api/README.md`](docs/api/README.md)
Interactive: http://localhost:8000/docs

---

## Observability

| Tool | URL | What it shows |
|------|-----|---------------|
| **Grafana** | http://localhost:3000 | API latency, simulation throughput, Kafka consumer lag |
| **Prometheus** | http://localhost:9090 | Raw metrics: `api_request_latency_seconds`, `simulation_total`, `queue_depth` |
| **API `/metrics`** | http://localhost:8000/metrics | Prometheus scrape endpoint |

SLO targets (production):
- API p99 latency < 2s
- Simulation success rate > 98%

---

## Troubleshooting

**`docker compose up` fails with port conflict**
Another service is using port 5432, 6379, or 9092. Stop the conflicting service or change the host port in `docker-compose.yml`.

**`uv sync` fails with Python version error**
Ensure Python 3.11+ is active: `python --version`. Use `pyenv` or `mise` to manage versions.

**API returns 401 unexpectedly**
Check `AUTH_REQUIRED` in your `.env`. It defaults to `false` — if it's been set to `true`, you need a JWT token. Run `POST /auth/dev-token` to get one.

**Simulation stays `pending` indefinitely**
The ARQ worker is not running. Start it with `uv run python -m api.worker` in a separate terminal.

**WebSocket connection drops immediately**
In dev, the Vite proxy must be running. Confirm you're accessing the dashboard via `http://localhost:5173` (not directly at port 8000). The Vite config proxies `/ws` to `ws://localhost:8000`.

**`check_env()` fails on a new Gym environment**
Observation values must be clipped to `[0, 1]`. See the lesson in `CLAUDE.md` under "S3 — Entorno gym".

---

## Contributing

1. Create a branch: `git checkout -b feat/my-feature`
2. Follow the conventions in `CLAUDE.md` (Python type hints, Pydantic v2, no `Any` without comment)
3. Run the full test suite: `uv run pytest tests/ -v`
4. Run linters: `uv run ruff check . && uv run mypy api/`
5. Open a PR against `main`

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*OPB AI Mastery Lab · From pipeline to decision.*
