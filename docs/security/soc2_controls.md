# SOC 2 Type II — Control Documentation
> Synthetic Persona Sandbox · Trust Services Criteria · 2026-05-06

---

## CC1 — Control Environment

### CC1.1 — COSO Principles: Demonstrates commitment to integrity and ethical values

- Access to production systems requires MFA via the identity provider.
- The `admin` role is the only role authorized to perform destructive operations (`DELETE /org/data`).
- All role assignments are audited in `audit_events` with actor, timestamp, and IP.

### CC1.2 — Board oversight

- Security decisions (auth model, data retention, GDPR) are tracked in `PLAN.md` with explicit justification.
- This document and `owasp_checklist.md` constitute the security baseline reviewed each sprint.

---

## CC2 — Communication and Information

### CC2.1 — Obtains and uses relevant quality information

- All API errors return structured JSON with `detail` field; no stack traces exposed externally.
- Prometheus metrics at `/metrics` expose request latency and simulation throughput.
- Grafana dashboards (see `infra/grafana/`) provide real-time visibility.

### CC2.2 — Communicates internally

- Audit log (`GET /org/audit`) accessible to `analyst` role and above within each org.
- Structured Python logging with `%(name)s` namespacing enables log aggregation (ELK/Loki).

---

## CC3 — Risk Assessment

### CC3.1 — Specifies suitable objectives

| Asset | Risk | Mitigation |
|-------|------|-----------|
| JWT secret | Compromise allows token forgery | Stored only in env vars; rotatable without code change |
| API keys | Leaked key grants org-scoped access | SHA-256 hash stored; raw key shown once; expiry enforced |
| Simulation runs | Cross-tenant data leakage | `org_id` filter on every query |
| Persona data | PII exposure via LLM | PII anonymized before LLM injection (architecture constraint) |
| Audit log | Tampering hides malicious activity | Append-only table; no `UPDATE`/`DELETE` permissions granted to app user |

### CC3.2 — Identifies and analyzes risk

- OWASP Top 10 checklist (`owasp_checklist.md`) reviewed each sprint.
- Dependency vulnerabilities tracked via Dependabot alerts.

---

## CC6 — Logical and Physical Access Controls

### CC6.1 — Logical access security software, infrastructure, and architectures

- **Authentication**: JWT (HS256 dev / RS256 prod) or SHA-256-hashed API keys.
- **Authorization**: RBAC with four roles (`viewer`, `analyst`, `marketer`, `admin`).
  - Permissions are additive: each role is a superset of the role below it.
  - Permission checks run on every endpoint via `require(Permission.X)` FastAPI dependency.
- **Session management**: JWTs have 1-hour TTL. API keys support configurable expiry (1–365 days).

### CC6.2 — Prior to issuing system credentials and granting system access

- New members are invited via `POST /org/members` by an admin; invitation is logged in `audit_events`.
- API keys are created with a named purpose and scoped role; creation is logged.

### CC6.3 — Removes access to protected information assets when appropriate

- Members removed via `DELETE /org/members/{user_id}` (logged).
- API keys revoked (soft-delete: `is_active = False`) via `DELETE /auth/keys/{id}` (logged).
- GDPR erasure via `DELETE /org/data` purges campaigns, simulations, segments, and API keys for the org.

### CC6.6 — Logical access security measures to protect against threats from outside the system

- CORS restricted to known frontend origin.
- `/auth/dev-token` disabled in production (`AUTH_MODE != "dev"`).
- Rate limiting on simulation endpoints (`RateLimitDep`).

### CC6.7 — Restricts the transmission of confidential information

- HTTPS enforced at the ingress/load-balancer layer (K8s TLS termination).
- Raw API keys are returned exactly once (on creation) and never stored in plaintext.
- Audit log includes IP addresses but not full request bodies.

---

## CC7 — System Operations

### CC7.1 — Detects and monitors for new vulnerabilities

- Dependabot configured for Python (`pyproject.toml`) and Node (`package.json`) dependencies.
- Container base images reviewed quarterly.

### CC7.2 — Monitors system components for anomalies

- Prometheus histograms alert on `p99 latency > 5s` and `error_rate > 1%`.
- Audit log reviewed monthly for anomalous patterns (bulk deletes, off-hours access).

### CC7.3 — Evaluates security events to determine whether they are security incidents

- All `4xx`/`5xx` responses are captured in the Prometheus `API_REQUEST_LATENCY` histogram with status code label.
- Failed auth attempts (`401`) logged at `WARNING` level with JWT error detail.

---

## CC8 — Change Management

### CC8.1 — Authorizes, designs, develops, configures, documents, tests, approves, and deploys changes

- All changes require a PR with passing CI (tests, type check, lint).
- Database migrations in `migrations/` are numbered, idempotent, and reviewed before deployment.
- Migration 004 adds `org_id` to existing tables with back-fill to the default org — no data loss.

---

## CC9 — Risk Mitigation

### CC9.1 — Identifies, selects, and develops risk mitigation activities

- **Data minimization**: Persona training data is anonymized and aggregated before LLM injection.
- **Isolation**: Each org's data is logically isolated via `org_id` column and query-level filtering.
- **Auditability**: Every mutating API call writes to `audit_events` (fire-and-forget; non-blocking).
- **Erasure**: GDPR `DELETE /org/data` cascade removes all operational data while retaining the organization record for billing continuity.

---

## Appendix A — Data Retention

| Data type | Retention | Deletion mechanism |
|-----------|-----------|-------------------|
| Simulation runs | Indefinite (org-scoped) | `DELETE /org/data` cascade |
| Audit events | 2 years | Scheduled purge job (planned) |
| API keys (revoked) | 90 days after revocation | Scheduled purge job (planned) |
| Persona embeddings (Qdrant) | Tied to segment lifecycle | `DELETE /segments/{id}` triggers Qdrant point deletion |

---

## Appendix B — Roles and Permissions Matrix

| Permission | viewer | analyst | marketer | admin |
|-----------|--------|---------|----------|-------|
| SIMULATIONS_READ | ✅ | ✅ | ✅ | ✅ |
| SIMULATIONS_RUN | — | — | ✅ | ✅ |
| SEGMENTS_READ | ✅ | ✅ | ✅ | ✅ |
| SEGMENTS_WRITE | — | — | ✅ | ✅ |
| CAMPAIGNS_READ | ✅ | ✅ | ✅ | ✅ |
| CAMPAIGNS_WRITE | — | — | ✅ | ✅ |
| ORG_MEMBERS_READ | ✅ | ✅ | ✅ | ✅ |
| ORG_MEMBERS_MANAGE | — | — | — | ✅ |
| ORG_KEYS_READ | — | — | ✅ | ✅ |
| ORG_KEYS_MANAGE | — | — | — | ✅ |
| ORG_AUDIT_READ | — | ✅ | ✅ | ✅ |
| ORG_DATA_DELETE | — | — | — | ✅ |
