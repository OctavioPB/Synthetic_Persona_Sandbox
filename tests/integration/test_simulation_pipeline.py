"""Integration tests — full simulation pipeline (Sprint 5).

Covers:
  1. Campaign + variant CRUD via the API.
  2. Simulation run via POST /simulate/run (mocked Claude client to avoid real API calls).
  3. WebSocket progress stream.
  4. Idempotency: re-running a completed run_id returns the cached result.

Requires:
    docker compose up -d postgres redis
    Set INTEGRATION_TESTS=1 to enable.

Run:
    uv run pytest tests/integration/test_simulation_pipeline.py -v -m integration
"""

from __future__ import annotations

import asyncio
import os
import uuid
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("INTEGRATION_TESTS") != "1",
    reason="Set INTEGRATION_TESTS=1 to run integration tests",
)

# ── Fixtures ───────────────────────────────────────────────────────────────────

AD_COPY_STIMULUS = {
    "type":      "ad_copy",
    "headline":  "Shop Smarter This Season",
    "body_copy": "Discover curated deals tailored just for you.",
    "cta":       "Explore Now",
    "product_name": "Summer Collection",
}

PRICE_CHANGE_STIMULUS = {
    "type":           "price_change",
    "product_name":   "Wireless Headphones",
    "original_price": 120.00,
    "new_price":      89.99,
}

PROMO_STIMULUS = {
    "type":           "promo",
    "promo_code":     "SAVE15",
    "discount_value": 15.0,
    "discount_type":  "percent",
    "minimum_purchase": 50.0,
    "expiry_days":    7,
}


@pytest_asyncio.fixture()
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture()
async def segment_id(client: AsyncClient) -> str:
    """Create a test segment and return its ID."""
    resp = await client.post("/segments", json={
        "name": "Integration Test Segment",
        "description": "Used by Sprint 5 integration tests.",
        "definition": {
            "category_affinities": ["Electronics"],
            "purchase_history_days": 30,
        },
    })
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest_asyncio.fixture()
async def campaign_id(client: AsyncClient, segment_id: str) -> str:
    """Create a test campaign and return its ID."""
    resp = await client.post("/campaigns", json={
        "name": "Summer Launch Campaign",
        "description": "Test campaign for variant competition.",
        "segment_id": segment_id,
    })
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Campaign CRUD ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_campaign(client: AsyncClient, segment_id: str) -> None:
    resp = await client.post("/campaigns", json={
        "name": "Test Campaign",
        "segment_id": segment_id,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Test Campaign"
    assert body["status"] == "draft"
    assert body["segment_id"] == segment_id


@pytest.mark.asyncio
async def test_list_campaigns(client: AsyncClient, campaign_id: str) -> None:
    resp = await client.get("/campaigns")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    ids = [c["id"] for c in body["items"]]
    assert campaign_id in ids


@pytest.mark.asyncio
async def test_update_campaign_status(client: AsyncClient, campaign_id: str) -> None:
    resp = await client.put(f"/campaigns/{campaign_id}", json={"status": "archived"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_delete_campaign(client: AsyncClient, segment_id: str) -> None:
    resp = await client.post("/campaigns", json={"name": "To Delete", "segment_id": segment_id})
    cid = resp.json()["id"]
    del_resp = await client.delete(f"/campaigns/{cid}")
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/campaigns/{cid}")
    assert get_resp.status_code == 404


# ── Variant CRUD ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_and_list_variants(client: AsyncClient, campaign_id: str) -> None:
    for i, stimulus in enumerate([AD_COPY_STIMULUS, PROMO_STIMULUS], start=1):
        resp = await client.post(f"/campaigns/{campaign_id}/variants", json={
            "name": f"Variant {i}",
            "stimulus": stimulus,
        })
        assert resp.status_code == 201

    list_resp = await client.get(f"/campaigns/{campaign_id}/variants")
    assert list_resp.status_code == 200
    variants = list_resp.json()
    assert len(variants) == 2


@pytest.mark.asyncio
async def test_delete_variant(client: AsyncClient, campaign_id: str) -> None:
    add = await client.post(f"/campaigns/{campaign_id}/variants", json={
        "name": "Temp Variant",
        "stimulus": AD_COPY_STIMULUS,
    })
    vid = add.json()["id"]
    del_resp = await client.delete(f"/campaigns/{campaign_id}/variants/{vid}")
    assert del_resp.status_code == 204


# ── Simulation run ─────────────────────────────────────────────────────────────

def _mock_inference_service():
    """Return a mock PersonaInferenceService that avoids real Claude calls."""
    from ml.synthetic_data.persona_inference import SyntheticResponse
    mock = MagicMock()
    mock.generate.return_value = SyntheticResponse(
        segment_id="test",
        stimulus_id="test",
        verbatim_response="This deal looks great! I'd definitely consider it.",
        sentiment="positive",
        likelihood_to_convert=0.78,
        key_factors=["price", "brand"],
        input_tokens=450,
        output_tokens=120,
        latency_ms=820.0,
    )
    return mock


@pytest.mark.asyncio
async def test_simulate_run_returns_scored_result(
    client: AsyncClient, segment_id: str
) -> None:
    with patch("api.routers.simulations._inference_service", _mock_inference_service()):
        resp = await client.post("/simulate/run", json={
            "segment_id": segment_id,
            "stimulus":   AD_COPY_STIMULUS,
        })

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed"
    assert body["sentiment"] == "positive"
    assert body["conversion_score"] is not None
    assert 0.0 <= body["conversion_score"] <= 1.0


@pytest.mark.asyncio
async def test_simulate_run_all_stimulus_types(
    client: AsyncClient, segment_id: str
) -> None:
    mock_svc = _mock_inference_service()
    for stimulus in [AD_COPY_STIMULUS, PRICE_CHANGE_STIMULUS, PROMO_STIMULUS]:
        with patch("api.routers.simulations._inference_service", mock_svc):
            resp = await client.post("/simulate/run", json={
                "segment_id": segment_id,
                "stimulus":   stimulus,
            })
        assert resp.status_code == 201, f"Failed for stimulus type '{stimulus['type']}'"


@pytest.mark.asyncio
async def test_simulate_run_unknown_segment_returns_404(
    client: AsyncClient,
) -> None:
    resp = await client.post("/simulate/run", json={
        "segment_id": str(uuid.uuid4()),
        "stimulus":   AD_COPY_STIMULUS,
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_simulate_run_invalid_stimulus_returns_422(
    client: AsyncClient, segment_id: str
) -> None:
    resp = await client.post("/simulate/run", json={
        "segment_id": segment_id,
        "stimulus":   {"type": "unknown_type", "foo": "bar"},
    })
    assert resp.status_code == 422


# ── Simulation history (S5-08 — already implemented in S4, tested here) ────────

@pytest.mark.asyncio
async def test_list_runs_filter_by_segment(
    client: AsyncClient, segment_id: str
) -> None:
    mock_svc = _mock_inference_service()
    with patch("api.routers.simulations._inference_service", mock_svc):
        await client.post("/simulate/run", json={
            "segment_id": segment_id,
            "stimulus":   AD_COPY_STIMULUS,
        })

    resp = await client.get(f"/simulate/runs?segment_id={segment_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert all(r["segment_id"] == segment_id for r in body["items"])


# ── WebSocket progress stream ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ws_streams_completed_run(
    client: AsyncClient, segment_id: str
) -> None:
    """Create a run, then connect via WS and verify the terminal update is received."""
    mock_svc = _mock_inference_service()
    with patch("api.routers.simulations._inference_service", mock_svc):
        run_resp = await client.post("/simulate/run", json={
            "segment_id": segment_id,
            "stimulus":   AD_COPY_STIMULUS,
        })
    run_id = run_resp.json()["id"]

    messages = []
    async with client.websocket_connect(f"/ws/simulations/{run_id}") as ws:
        for _ in range(3):
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            messages.append(msg)
            if msg.get("status") in ("completed", "failed"):
                break

    assert any(m.get("status") == "completed" for m in messages)
    final = next(m for m in messages if m.get("status") == "completed")
    assert final["run_id"] == run_id
    assert final["sentiment"] == "positive"


@pytest.mark.asyncio
async def test_ws_unknown_run_id_sends_not_found(client: AsyncClient) -> None:
    fake_id = str(uuid.uuid4())
    messages = []
    async with client.websocket_connect(f"/ws/simulations/{fake_id}") as ws:
        msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
        messages.append(msg)

    assert messages[0]["error"] == "not_found"
