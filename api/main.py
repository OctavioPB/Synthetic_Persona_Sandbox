import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import health

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Synthetic Persona Sandbox",
    description="AI-powered marketing simulation with synthetic customer personas.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Synthetic Persona Sandbox API starting up.")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Synthetic Persona Sandbox API shutting down.")
