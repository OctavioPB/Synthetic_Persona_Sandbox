# Engineering

How to work on this codebase: tooling, tests, CI, conventions and known gaps.

## Toolchain

| Area | Tools |
|------|-------|
| Python | 3.11+, uv, Ruff (lint and format), mypy in strict mode, pytest |
| Frontend | Node 20, Vite, React 18, TypeScript, ESLint, Storybook, Playwright |
| CI and security | GitHub Actions, CodeQL, Dependabot |

## Local setup

```bash
uv sync --extra dev
cd dashboard && npm ci && cd ..
cp .env.example .env    # then fill in the values you need
```

`ENV`, `AUTH_REQUIRED` and `AUTH_MODE` control the safety guards; see
[ARCHITECTURE.md](ARCHITECTURE.md#security-and-tenancy).

## Checks to run before pushing

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy api/ ingestion/ ml/
uv run pytest tests/unit/

cd dashboard && npm run lint && npm run type-check && npm run build
```

## Test layout

| Folder | Needs | Covers |
|--------|-------|--------|
| `tests/unit/` | Nothing | Schemas, prompt building, scoring, anonymizer, API models, audit regressions, evaluation logic |
| `tests/integration/test_regression.py` | PostgreSQL and Redis | Health, auth, CRUD, enqueue, cross-tenant isolation, API keys |
| `tests/integration/test_pipeline.py`, `test_simulation_pipeline.py` | The full stack | Kafka to API, end-to-end simulation |
| `tests/load/locustfile.py` | A running API | 20 concurrent users |
| `dashboard/tests/e2e/` | Dev server | Campaign flow (Playwright) |

### Running the integration tests locally

They need PostgreSQL with the migrations applied, and Redis. Throwaway containers on other
ports avoid clashing with other local services:

```bash
docker run -d --name spb-test-pg -e POSTGRES_DB=synthetic_persona_test \
  -e POSTGRES_USER=spb_user -e POSTGRES_PASSWORD=changeme \
  -p 127.0.0.1:55432:5432 postgres:16-alpine
docker run -d --name spb-test-redis -p 127.0.0.1:56379:6379 redis:7.2-alpine

for f in migrations/*.sql; do
  docker exec -i spb-test-pg psql -U spb_user -d synthetic_persona_test -v ON_ERROR_STOP=1 < "$f"
done

POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55432 POSTGRES_DB=synthetic_persona_test \
REDIS_HOST=127.0.0.1 REDIS_PORT=56379 ENV=test \
  uv run pytest tests/integration/test_regression.py

docker rm -f spb-test-pg spb-test-redis
```

Use `127.0.0.1`, not `localhost`. On Windows `localhost` can resolve to IPv6 first and time
out the queue connection.

The test client keeps module-level database and Redis pools, and each test runs on its own
event loop. A fixture releases the pools after every test; without it, tests fail with
"attached to a different loop".

## CI pipeline

| Job | Checks |
|-----|--------|
| Python lint | Ruff lint, Ruff format, mypy |
| Unit tests | `tests/unit/`, no services |
| Avro schemas | Every `.avsc` file parses |
| Integration | Starts PostgreSQL and Redis, applies migrations, runs the regression suite |
| Dashboard | ESLint, type check, production build |
| `ci-success` | One gate for branch protection; fails if any job failed or was cancelled |

Workflows run with read-only permissions, cancel superseded runs and have timeouts. CodeQL
scans Python and TypeScript weekly and on pull requests. Code scanning must be enabled in
the repository settings for its results to appear.

## Dependency policy

- Python dependencies are locked in `uv.lock`; the dashboard in `package-lock.json`.
- Dependabot opens weekly pip and npm updates and monthly GitHub Actions and Docker updates.
- **The Anthropic SDK is capped below 1.0.** Version 1.0 removes the `temperature` argument
  that `ml/synthetic_data/claude_client.py` sends, and 2.0 moves to an API version that
  rejects it. `pyproject.toml` holds the cap and Dependabot ignores 1.0 and later. Lift both
  only together with removing `temperature` from the client.

## Conventions

- **Never block the event loop.** Model and Qdrant calls are synchronous, so they run
  through `asyncio.to_thread`.
- **Commit, then publish.** Commit a database row before enqueueing work that updates it.
- **Scope everything by `org_id`**, including cache keys.
- **A session you open, you commit.** Sessions created outside the request dependency don't
  commit by themselves.
- **Keep metric labels bounded.** Label by route template, never by raw path with ids.
- **Fail fast in production.** Insecure defaults stop the process instead of logging a
  warning.
- **Type everything.** mypy runs in strict mode; an `Any` or a type-ignore needs a reason.
- **Prompt changes need a measurement.** Run `scripts/evaluate_upworthy.py` before and
  after. It records prompt fingerprints, so you can tell which results match which prompt.
  See [EVALUATION.md](EVALUATION.md).

## Common tasks

**Add a stimulus goal.** Add the value to `Goal` in `ml/synthetic_data/stimulus_schema.py`,
add its wording to `_GOAL_WORDING` in `persona_context_builder.py`, add it to `GOALS` in
`dashboard/src/components/StimulusBuilder.tsx` and to `StimulusGoal` in
`dashboard/src/store/campaignStore.ts`, and add a case to `tests/unit/test_stimulus_goal.py`.

**Add a migration.** Add the next numbered `.sql` file to `migrations/`, safe to re-run.
CI and the PostgreSQL container apply files in name order.

**Add an endpoint.** Protect it with `Depends(require(Permission.X))`, filter by
`claims.org_id`, and add a regression test that another organization can't reach the data.

## Known gaps

- Dark mode: some headings and card text are nearly unreadable.
- The dashboard uses many inline styles and hard-coded colors instead of design tokens.
- The synchronous simulation endpoint has no rate limit.
- The package version (`pyproject.toml`, 0.1.0) and the API version (1.0.0) differ.
- Playwright and load tests are not part of CI.
- Segment detail shows affinity percentages computed from list order, not from data.
