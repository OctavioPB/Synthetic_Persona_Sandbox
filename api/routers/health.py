"""Liveness endpoint."""

import time

from fastapi import APIRouter
from pydantic import BaseModel

from api import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: float


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe — returns 200 when the API process is running."""
    return HealthResponse(status="ok", version=__version__, timestamp=time.time())
