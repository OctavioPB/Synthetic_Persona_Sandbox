"""Unit tests for the /health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from api import __version__
from api.main import app


@pytest.mark.asyncio
async def test_health_returns_200() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_schema() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert isinstance(body["timestamp"], float)
