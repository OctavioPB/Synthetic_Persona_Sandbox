# GA Go/No-Go Checklist — Synthetic Persona Sandbox v1.0.0
> Sprint 10 · 2026-05-06 · Requires sign-off from all team leads before release tag is pushed.

---

## Instructions

- Each owner must mark their section ✅ and add their initials + date.
- A single ❌ blocks the release — open a P0 issue and reschedule.
- After all sections are ✅, create the git tag `v1.0.0` and push to trigger the production deploy workflow.

---

## 1 — Infrastructure (DevOps Lead)

| # | Check | Status |
|---|-------|--------|
| 1.1 | All K8s manifests applied to production cluster without errors | ☐ |
| 1.2 | HPA configured for `spb-api` (min 2 / max 10) and `spb-worker` (min 2 / max 8) | ☐ |
| 1.3 | Ingress TLS cert issued by cert-manager (valid for ≥ 89 days) | ☐ |
| 1.4 | `spb-pg-backup` CronJob executed successfully at least once (verify S3 object) | ☐ |
| 1.5 | Restore procedure tested: backup from S3 applied to staging DB without data loss | ☐ |
| 1.6 | Zero-downtime deploy demonstrated: `kubectl rollout status` confirmed during staging deploy | ☐ |
| 1.7 | Rollback tested: `kubectl rollout undo` restores previous version in < 60s | ☐ |

**Sign-off:** ___________________________ Date: ___________

---

## 2 — Observability (DevOps Lead)

| # | Check | Status |
|---|-------|--------|
| 2.1 | Prometheus scraping `spb-api` pods via `ServiceMonitor` (verify in Prometheus targets) | ☐ |
| 2.2 | Grafana dashboards loading: API latency, simulation throughput, Kafka consumer lag | ☐ |
| 2.3 | Loki receiving logs from `spb-api` and `spb-worker` pods | ☐ |
| 2.4 | SLO alert `SPBApiLatencySLOBurn1h` fires in test scenario (manually trigger with `promtool`) | ☐ |
| 2.5 | SLO alert `SPBSimulationErrorRateSLOBurn1h` fires in test scenario | ☐ |
| 2.6 | `SPBApiDown` alert tested: scale down all pods, alert fires within 2 min | ☐ |

**Sign-off:** ___________________________ Date: ___________

---

## 3 — Security (Security Lead)

| # | Check | Status |
|---|-------|--------|
| 3.1 | `POST /simulate/run` without auth returns 401 (verify with `curl -s` — no token) | ☐ |
| 3.2 | Org A cannot access Org B's data (cross-tenant test from `test_regression.py::test_cross_tenant_isolation`) | ☐ |
| 3.3 | GDPR `DELETE /org/data` tested on staging: all campaigns, simulations, segments, keys deleted | ☐ |
| 3.4 | API key shown only on creation; subsequent `GET /auth/keys` does not return raw key | ☐ |
| 3.5 | `POST /auth/dev-token` returns 404 in production (`AUTH_MODE != dev`) | ☐ |
| 3.6 | JWT with expired `exp` claim returns 401 | ☐ |
| 3.7 | All security headers present: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` | ☐ |
| 3.8 | OWASP checklist reviewed — all ⚠️ items have accepted risk documentation | ☐ |
| 3.9 | `JWT_SECRET` confirmed rotated from dev default — not `dev-secret-change-in-production` | ☐ |

**Sign-off:** ___________________________ Date: ___________

---

## 4 — Backend Quality (Backend Lead)

| # | Check | Status |
|---|-------|--------|
| 4.1 | `uv run pytest tests/unit/ -v` — all tests pass (0 failures) | ☐ |
| 4.2 | `uv run pytest tests/integration/test_regression.py -v` — all tests pass | ☐ |
| 4.3 | `uv run mypy api/` — 0 errors | ☐ |
| 4.4 | `uv run ruff check .` — 0 violations | ☐ |
| 4.5 | Migration `004_security_and_tenancy.sql` applied to production DB (idempotent re-run confirms no-op) | ☐ |
| 4.6 | `GET /simulate/runs/{id}` confirmed cache-hit for completed runs (Redis `monitor` shows `GET spb:run:*`) | ☐ |
| 4.7 | Rate limiter on `POST /simulate/run` confirmed: 11th request in 1 min returns 429 | ☐ |

**Sign-off:** ___________________________ Date: ___________

---

## 5 — Frontend Quality (Frontend Lead)

| # | Check | Status |
|---|-------|--------|
| 5.1 | `npm run build` succeeds with 0 TypeScript errors | ☐ |
| 5.2 | `npm run lint` — 0 ESLint errors | ☐ |
| 5.3 | Campaign Launcher flow tested end-to-end in production Chrome (create → launch → results) | ☐ |
| 5.4 | Analytics page: CSV export produces a valid file | ☐ |
| 5.5 | Dark mode: toggle persists across page refresh | ☐ |
| 5.6 | Login page: `VITE_AUTH_REQUIRED=true` redirects unauthenticated users | ☐ |
| 5.7 | Nav shows `email · role` after login; Logout button clears token | ☐ |
| 5.8 | Playwright E2E suite passes: `npm run e2e` (0 failures) | ☐ |

**Sign-off:** ___________________________ Date: ___________

---

## 6 — Performance (Backend + DevOps)

| # | Check | Status |
|---|-------|--------|
| 6.1 | `GET /health` p99 < 50ms under 100 concurrent requests (locust report attached) | ☐ |
| 6.2 | `POST /simulate/run` p99 < 10s at 20 concurrent simulations (Sprint 6 load test re-verified) | ☐ |
| 6.3 | `GET /simulate/runs/{id}` cache hit latency < 5ms (confirmed via Redis latency monitor) | ☐ |
| 6.4 | API pod memory stays below 800Mi under load (Grafana memory graph attached) | ☐ |

**Sign-off:** ___________________________ Date: ___________

---

## 7 — Documentation (All Leads)

| # | Check | Status |
|---|-------|--------|
| 7.1 | `docs/guides/first_simulation.md` reviewed and accurate | ☐ |
| 7.2 | `docs/api/README.md` — all endpoints listed, examples tested | ☐ |
| 7.3 | `docs/security/owasp_checklist.md` — all ✅ items verified | ☐ |
| 7.4 | `docs/security/soc2_controls.md` — reviewed by security lead | ☐ |
| 7.5 | `CLAUDE.md` Sprint 10 status updated to `[x] Completado` | ☐ |
| 7.6 | `PLAN.md` Go/No-Go checklist marked complete | ☐ |

**Sign-off:** ___________________________ Date: ___________

---

## Final Decision

| Outcome | Requires |
|---------|----------|
| ✅ **GO** — push `v1.0.0` tag | All 7 sections signed off |
| ❌ **NO-GO** | Any single check fails |

**Release decision:** ☐ GO &nbsp;&nbsp; ☐ NO-GO

**Release manager:** ___________________________ Date: ___________

**Git tag command (after GO):**
```bash
git tag -a v1.0.0 -m "GA Release — Synthetic Persona Sandbox v1.0.0"
git push origin v1.0.0
```

This triggers the `deploy.yml` workflow with production environment approval gate.
