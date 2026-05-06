# API Reference — Synthetic Persona Sandbox

> **Base URL (production):** `https://api.syntheticpersonasandbox.com`
> **Base URL (dev):** `http://localhost:8000`
>
> Interactive docs (Swagger UI): `{base_url}/docs`
> ReDoc: `{base_url}/redoc`
> OpenAPI JSON: `{base_url}/openapi.json`

---

## Authentication

All endpoints (except `/health`, `/metrics`, and `/auth/dev-token` in dev mode) require authentication.

### Bearer JWT

```http
Authorization: Bearer <token>
```

Obtain a token:
- **Dev mode** (`AUTH_MODE=dev`): `POST /auth/dev-token`
- **Production**: Authenticate via your identity provider and use the returned JWT.

### API Key

```http
X-API-Key: spb_<key>
```

Create a key via `POST /auth/keys`. Keys are scoped to a role and support expiry.

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `POST /simulate/run` | 10 requests/minute per org |
| All other endpoints | No hard limit (fair use) |

Exceeded limits return `429 Too Many Requests`.

---

## Endpoints by Resource

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Liveness check — returns `{"status": "ok"}` |
| `GET` | `/metrics` | None* | Prometheus metrics (*restrict at network layer in prod) |

---

### Authentication (`/auth`)

| Method | Path | Role Required | Description |
|--------|------|---------------|-------------|
| `POST` | `/auth/dev-token` | None (dev only) | Issue a dev JWT |
| `POST` | `/auth/keys` | `admin` | Create an API key |
| `GET`  | `/auth/keys` | `marketer` | List active API keys for the org |
| `DELETE` | `/auth/keys/{key_id}` | `admin` | Revoke an API key |

**Create a dev token**
```http
POST /auth/dev-token
Content-Type: application/json

{
  "email": "dev@myorg.com",
  "role": "admin"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### Organization (`/org`)

| Method | Path | Role Required | Description |
|--------|------|---------------|-------------|
| `GET` | `/org` | `viewer` | Get current org profile |
| `GET` | `/org/members` | `viewer` | List org members |
| `POST` | `/org/members` | `admin` | Invite a member |
| `DELETE` | `/org/members/{user_id}` | `admin` | Remove a member |
| `GET` | `/org/audit` | `analyst` | Paginated audit log |
| `DELETE` | `/org/data` | `admin` | GDPR: delete all org data (irreversible) |

---

### Segments (`/segments`)

| Method | Path | Role Required | Description |
|--------|------|---------------|-------------|
| `POST` | `/segments` | `marketer` | Create a segment |
| `GET`  | `/segments` | `viewer` | List segments (paginated) |
| `GET`  | `/segments/{id}` | `viewer` | Get a segment |
| `PUT`  | `/segments/{id}` | `marketer` | Update a segment |
| `DELETE` | `/segments/{id}` | `marketer` | Delete a segment |

**Segment definition schema**
```json
{
  "name": "Gen Z — Madrid",
  "description": "Urban young adults",
  "definition": {
    "age_range": { "min_age": 18, "max_age": 24 },
    "geo": { "city": "Madrid", "country": "Spain" },
    "category_affinities": ["Electronics", "Fashion"],
    "purchase_history_days": 90
  }
}
```

---

### Simulations (`/simulate`)

| Method | Path | Role Required | Description |
|--------|------|---------------|-------------|
| `POST` | `/simulate/run` | `marketer` | Enqueue async simulation (202) |
| `POST` | `/simulate/run/sync` | `marketer` | Run simulation synchronously (201) |
| `GET`  | `/simulate/runs` | `viewer` | List runs (paginated, filterable) |
| `GET`  | `/simulate/runs/{id}` | `viewer` | Get a single run |

**WebSocket — live progress**
```
ws://api.syntheticpersonasandbox.com/ws/simulations/{run_id}
```
Messages:
```json
{ "status": "running",   "progress": 0.5 }
{ "status": "completed", "conversion_score": 0.74, "sentiment": "positive" }
{ "status": "failed",    "error_detail": "LLM timeout" }
```
Terminal statuses: `completed`, `failed`, `error` — close the connection after receiving one.

**Run request body**
```json
{
  "segment_id": "uuid",
  "stimulus": {
    "type": "ad_copy",
    "headline": "Summer Sale",
    "body_copy": "Up to 50% off selected items.",
    "cta": "Shop Now"
  },
  "temperature": 0.7
}
```

Stimulus types: `ad_copy` | `price_change` | `promo`

---

### Campaigns (`/campaigns`)

| Method | Path | Role Required | Description |
|--------|------|---------------|-------------|
| `POST` | `/campaigns` | `marketer` | Create a campaign |
| `GET`  | `/campaigns` | `viewer` | List campaigns |
| `GET`  | `/campaigns/{id}` | `viewer` | Get a campaign |
| `PUT`  | `/campaigns/{id}` | `marketer` | Update a campaign |
| `DELETE` | `/campaigns/{id}` | `marketer` | Delete a campaign |
| `POST` | `/campaigns/{id}/variants` | `marketer` | Add a variant |
| `GET`  | `/campaigns/{id}/variants` | `viewer` | List variants |
| `DELETE` | `/campaigns/{id}/variants/{vid}` | `marketer` | Remove a variant |

---

## Error Responses

All errors follow the FastAPI default format:

```json
{ "detail": "Human-readable error message." }
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request (e.g. cannot remove yourself from org) |
| `401` | Authentication required or invalid token |
| `403` | Insufficient role for this operation |
| `404` | Resource not found (or not visible to your org) |
| `422` | Validation error (malformed UUID, missing field, etc.) |
| `429` | Rate limit exceeded |
| `502` | LLM inference failed (retry after a moment) |

---

## RBAC Role Summary

| Role | Permissions |
|------|------------|
| `viewer` | Read segments, campaigns, simulation runs, org members |
| `analyst` | `viewer` + read audit log |
| `marketer` | `analyst` + run simulations, write segments & campaigns, read API keys |
| `admin` | All permissions including member management, API key management, org data deletion |

---

## Pagination

List endpoints support:
```
GET /segments?page=1&size=20
GET /simulate/runs?page=2&size=50&status=completed&segment_id=<uuid>
GET /org/audit?size=100&offset=0
```

Response envelope:
```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "size": 20
}
```
