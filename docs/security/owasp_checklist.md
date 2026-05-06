# OWASP Top 10 — Mitigation Checklist
> Synthetic Persona Sandbox · Sprint 9 · 2026-05-06

---

## A01 — Broken Access Control

| Control | Status | Implementation |
|---------|--------|----------------|
| All routes enforce authentication | ✅ | `get_current_user` dependency; `AUTH_REQUIRED=true` in production |
| RBAC on every mutating endpoint | ✅ | `require(Permission.X)` dependency factory; `ROLE_PERMISSIONS` frozensets |
| Org-scoped data isolation | ✅ | All queries filter by `claims.org_id`; no cross-tenant data leakage |
| Self-removal prevention | ✅ | `DELETE /org/members/{user_id}` rejects `user_id == claims.sub` |
| Admin-only destructive ops | ✅ | `DELETE /org/data` checks `claims.is_admin` before cascade |

---

## A02 — Cryptographic Failures

| Control | Status | Implementation |
|---------|--------|----------------|
| Secrets never in source code | ✅ | `JWT_SECRET` loaded from env; `.env` in `.gitignore` |
| API keys stored as hashes | ✅ | SHA-256 hash stored in `api_keys.key_hash`; raw key shown once on creation |
| JWT algorithm pinned | ✅ | `decode_token` specifies `algorithms=["HS256"]` — no `alg: none` |
| HTTPS enforced in production | ⚠️ | Configured at the load-balancer/ingress layer (K8s TLS termination) — not at app layer |
| Passwords not stored | ✅ | No local passwords; auth delegated to identity provider or API keys |

---

## A03 — Injection

| Control | Status | Implementation |
|---------|--------|----------------|
| Parameterized queries everywhere | ✅ | SQLAlchemy ORM with bound parameters — no raw SQL string formatting |
| No raw SQL outside `db.py` | ✅ | CLAUDE.md constraint: raw SQL only in `api/services/db.py` |
| Pydantic validation on all inputs | ✅ | All request bodies are Pydantic models; FastAPI rejects malformed input at 422 |
| JSONB fields validated at write | ✅ | `_parse_stimulus()` validates stimulus before persistence |

---

## A04 — Insecure Design

| Control | Status | Implementation |
|---------|--------|----------------|
| Threat model documented | ✅ | This document + SOC 2 controls cover the threat surface |
| Principle of least privilege | ✅ | `viewer ⊂ analyst ⊂ marketer ⊂ admin` role hierarchy; API keys scoped to a role |
| Audit trail for all mutations | ✅ | `audit_write_middleware` + `log_event()` fire-and-forget service |
| GDPR deletion supported | ✅ | `DELETE /org/data` cascade purges all org data; organization record retained |

---

## A05 — Security Misconfiguration

| Control | Status | Implementation |
|---------|--------|----------------|
| CORS restricted to known origins | ✅ | `allow_origins=["http://localhost:5173"]` in dev; override via env in prod |
| Debug endpoints disabled in prod | ✅ | `POST /auth/dev-token` gated by `AUTH_MODE == "dev"` |
| Prometheus metrics not public | ⚠️ | `/metrics` endpoint has no auth — should be blocked at network layer in prod |
| Error messages don't leak internals | ✅ | Generic error messages; stack traces only in server logs |

---

## A06 — Vulnerable and Outdated Components

| Control | Status | Implementation |
|---------|--------|----------------|
| Dependency pinning | ✅ | `pyproject.toml` + `uv.lock`; `package.json` + `package-lock.json` |
| Security updates | 🔄 | Dependabot / Renovate configured in CI (see `.github/dependabot.yml`) |
| Container base images | ⚠️ | Distroless images planned; currently using `python:3.11-slim` |

---

## A07 — Identification and Authentication Failures

| Control | Status | Implementation |
|---------|--------|----------------|
| JWT expiry enforced | ✅ | `exp` claim validated by `PyJWT`; default 1-hour TTL |
| API key expiry supported | ✅ | `expires_at` column checked on every API key lookup |
| Inactive keys rejected | ✅ | `is_active = False` check in `_validate_api_key()` |
| Brute-force protection | ⚠️ | Rate limiter (`RateLimitDep`) on simulation endpoints; not yet on auth endpoints |
| Token invalidation on logout | ⚠️ | JWTs are stateless — revocation requires a denylist (future: Redis blocklist) |

---

## A08 — Software and Data Integrity Failures

| Control | Status | Implementation |
|---------|--------|----------------|
| Idempotent DAGs | ✅ | All Airflow DAGs safe to re-run (CLAUDE.md constraint) |
| Job deduplication | ✅ | ARQ `_job_id = str(run.id)` prevents duplicate simulation jobs |
| Input validation before enqueue | ✅ | `_parse_stimulus()` validates before the job is queued |

---

## A09 — Security Logging and Monitoring Failures

| Control | Status | Implementation |
|---------|--------|----------------|
| Audit log for all mutations | ✅ | `audit_events` table; `audit_write_middleware` captures POST/PUT/PATCH/DELETE |
| Structured logging | ✅ | Python `logging` module with `%(name)s` namespaces |
| Request IP captured | ✅ | `_get_client_ip()` respects `X-Forwarded-For` for proxied requests |
| Audit log protected | ✅ | Only `analyst` role and above can read `GET /org/audit` |
| Prometheus metrics | ✅ | `API_REQUEST_LATENCY` histogram; `SIMULATION_TOTAL` counter |

---

## A10 — Server-Side Request Forgery (SSRF)

| Control | Status | Implementation |
|---------|--------|----------------|
| No user-controlled URLs fetched | ✅ | API does not fetch external URLs based on user input |
| LLM prompts sanitized | ✅ | Segment definitions are structured Pydantic models, not raw URLs |
| Qdrant / Redis access internal only | ✅ | Services bound to `localhost` or internal Docker network |

---

## Legend
- ✅ Implemented and verified
- ⚠️ Partially mitigated — noted risk accepted or deferred to infrastructure layer
- 🔄 Automated / ongoing
