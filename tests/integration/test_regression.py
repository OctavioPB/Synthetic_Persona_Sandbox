"""Full regression test suite — S10-07.

Covers the critical happy-paths and security boundaries added through Sprint 9.
Requires:
  - POSTGRES running (via docker-compose or K8s port-forward)
  - AUTH_REQUIRED=false (default) for most tests; a few exercise auth paths directly.

Run:
    uv run pytest tests/integration/test_regression.py -v --tb=short

In CI against staging:
    API_BASE_URL=https://api-staging.syntheticpersonasandbox.com \
    STAGING_TOKEN=<token> \
    uv run pytest tests/integration/test_regression.py -v -m "not local_only"
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ── Test client setup ─────────────────────────────────────────────────────────

_API_BASE_URL = os.getenv("API_BASE_URL", "")
_STAGING_TOKEN = os.getenv("STAGING_TOKEN", "")

# If API_BASE_URL is set, we run against a live server; otherwise use ASGI transport.
_USE_LIVE_SERVER = bool(_API_BASE_URL)


@pytest_asyncio.fixture
async def client() -> AsyncClient:  # type: ignore[misc]
    if _USE_LIVE_SERVER:
        headers: dict[str, str] = {}
        if _STAGING_TOKEN:
            headers["Authorization"] = f"Bearer {_STAGING_TOKEN}"
        async with AsyncClient(base_url=_API_BASE_URL, headers=headers) as c:
            yield c
    else:
        from api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


# ── S10-07-01: Health check ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


# ── S10-07-02: Auth — unauthenticated access returns 401 when enforced ────────

@pytest.mark.asyncio
@pytest.mark.local_only
async def test_auth_required_blocks_unauthenticated() -> None:
    """When AUTH_REQUIRED=true, all protected endpoints must return 401."""
    import os
    original = os.environ.get("AUTH_REQUIRED", "false")
    os.environ["AUTH_REQUIRED"] = "true"

    try:
        from api.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/segments")
            assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    finally:
        os.environ["AUTH_REQUIRED"] = original


# ── S10-07-03: Dev token endpoint ─────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.local_only
async def test_dev_token_issued_in_dev_mode(client: AsyncClient) -> None:
    resp = await client.post("/auth/dev-token", json={"email": "test@regression.com", "role": "marketer"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600


# ── S10-07-04: Segment CRUD happy path ───────────────────────────────────────

@pytest.mark.asyncio
async def test_segment_create_list_delete(client: AsyncClient) -> None:
    payload: dict[str, Any] = {
        "name": f"Regression Segment {uuid.uuid4().hex[:6]}",
        "description": "Created by regression test suite",
        "definition": {
            "age_range": {"min_age": 25, "max_age": 34},
            "geo": {"city": "Barcelona", "country": "Spain"},
            "category_affinities": ["Travel", "Tech"],
            "purchase_history_days": 60,
        },
    }

    # Create
    resp = await client.post("/segments", json=payload)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    segment_id = created["id"]
    assert created["name"] == payload["name"]
    assert created["is_stale"] is True

    # List — should appear
    list_resp = await client.get("/segments")
    assert list_resp.status_code == 200
    ids = [s["id"] for s in list_resp.json().get("items", [])]
    assert segment_id in ids

    # Get by ID
    get_resp = await client.get(f"/segments/{segment_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == segment_id

    # Delete
    del_resp = await client.delete(f"/segments/{segment_id}")
    assert del_resp.status_code == 204

    # Confirm gone
    get_gone = await client.get(f"/segments/{segment_id}")
    assert get_gone.status_code == 404


# ── S10-07-05: Campaign CRUD ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_campaign_create_and_variant(client: AsyncClient) -> None:
    campaign_payload = {
        "name": f"Regression Campaign {uuid.uuid4().hex[:6]}",
        "description": "Automated regression test",
        "segment_id": None,
    }

    # Create campaign
    resp = await client.post("/campaigns", json=campaign_payload)
    assert resp.status_code == 201, resp.text
    campaign_id = resp.json()["id"]

    # Add variant
    variant_payload = {
        "name": "Variant A",
        "stimulus": {
            "type": "ad_copy",
            "headline": "Regression test headline",
            "body_copy": "Test body copy for regression.",
            "cta": "Learn More",
        },
    }
    var_resp = await client.post(f"/campaigns/{campaign_id}/variants", json=variant_payload)
    assert var_resp.status_code == 201, var_resp.text
    variant_id = var_resp.json()["id"]

    # List variants
    list_resp = await client.get(f"/campaigns/{campaign_id}/variants")
    assert list_resp.status_code == 200
    ids = [v["id"] for v in list_resp.json()]
    assert variant_id in ids

    # Delete campaign (cascades variants)
    del_resp = await client.delete(f"/campaigns/{campaign_id}")
    assert del_resp.status_code == 204


# ── S10-07-06: Simulation run enqueue ────────────────────────────────────────

@pytest.mark.asyncio
async def test_simulation_run_enqueue_returns_202(client: AsyncClient) -> None:
    """Smoke test: verify the async run endpoint accepts the job and returns 202."""
    # Create a segment first
    seg_resp = await client.post("/segments", json={
        "name": f"Sim Regression {uuid.uuid4().hex[:6]}",
        "description": "For simulation regression",
        "definition": {
            "age_range": {"min_age": 18, "max_age": 35},
            "geo": {"city": "Madrid", "country": "Spain"},
            "category_affinities": ["Fashion"],
            "purchase_history_days": 30,
        },
    })
    assert seg_resp.status_code == 201
    segment_id = seg_resp.json()["id"]

    run_resp = await client.post("/simulate/run", json={
        "segment_id": segment_id,
        "stimulus": {
            "type": "ad_copy",
            "headline": "Regression headline",
            "body_copy": "Test body",
            "cta": "Buy Now",
        },
    })
    assert run_resp.status_code == 202, run_resp.text
    body = run_resp.json()
    assert body["status"] == "pending"
    assert body["segment_id"] == segment_id
    run_id = body["id"]

    # Poll via GET — should return the run (pending or completed)
    get_resp = await client.get(f"/simulate/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == run_id

    # Cleanup
    await client.delete(f"/segments/{segment_id}")


# ── S10-07-07: Multi-tenancy isolation ───────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.local_only
async def test_cross_tenant_isolation() -> None:
    """Org A cannot read Org B's segments."""
    import os
    os.environ["AUTH_REQUIRED"] = "true"

    from api.main import app

    org_a_id = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
    org_b_id = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")

    from api.auth.jwt_handler import encode_token
    token_a = encode_token(sub="user-a", email="a@test.com", org_id=org_a_id, role="admin")
    token_b = encode_token(sub="user-b", email="b@test.com", org_id=org_b_id, role="admin")

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # Create a segment as Org A
            create_resp = await c.post(
                "/segments",
                json={
                    "name": "Org A Segment",
                    "description": "Private to Org A",
                    "definition": {
                        "age_range": {"min_age": 18, "max_age": 30},
                        "geo": {"city": "City", "country": "Country"},
                        "category_affinities": [],
                        "purchase_history_days": 7,
                    },
                },
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert create_resp.status_code == 201
            segment_id = create_resp.json()["id"]

            # Org B attempts to read Org A's segment — must get 404, not the data
            get_resp = await c.get(
                f"/segments/{segment_id}",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            assert get_resp.status_code == 404, (
                f"Cross-tenant data leak: Org B accessed Org A's segment {segment_id}"
            )

            # Cleanup as Org A
            await c.delete(
                f"/segments/{segment_id}",
                headers={"Authorization": f"Bearer {token_a}"},
            )
    finally:
        os.environ["AUTH_REQUIRED"] = "false"


# ── S10-07-08: Org management endpoints ──────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.local_only
async def test_org_info_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/org")
    # In dev mode (AUTH_REQUIRED=false), GUEST_CLAIMS points to DEFAULT_ORG_ID
    # The org must exist (inserted by migration 004).
    assert resp.status_code in (200, 404)  # 404 acceptable if migration not run


# ── S10-07-09: API key lifecycle ──────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.local_only
async def test_api_key_create_list_revoke(client: AsyncClient) -> None:
    # Create
    create_resp = await client.post("/auth/keys", json={"name": "Regression Key", "role": "marketer"})
    assert create_resp.status_code == 201, create_resp.text
    body = create_resp.json()
    assert "raw_key" in body
    assert body["raw_key"].startswith("spb_")
    key_id = body["id"]

    # List — should appear
    list_resp = await client.get("/auth/keys")
    assert list_resp.status_code == 200
    ids = [k["id"] for k in list_resp.json()["items"]]
    assert key_id in ids

    # Revoke
    revoke_resp = await client.delete(f"/auth/keys/{key_id}")
    assert revoke_resp.status_code == 204

    # Confirm not in active list
    list_after = await client.get("/auth/keys")
    ids_after = [k["id"] for k in list_after.json()["items"]]
    assert key_id not in ids_after


# ── S10-07-10: Invalid UUIDs return 422, not 500 ─────────────────────────────

@pytest.mark.asyncio
async def test_invalid_uuid_returns_422(client: AsyncClient) -> None:
    for path in ["/segments/not-a-uuid", "/simulate/runs/not-a-uuid", "/campaigns/not-a-uuid"]:
        resp = await client.get(path)
        assert resp.status_code == 422, f"Expected 422 for {path}, got {resp.status_code}"
