"""ARQ worker entry-point.

Usage:
    uv run python -m api.worker
"""
import asyncio

from arq.worker import create_worker

from api.workers.simulation_worker import WorkerSettings

if __name__ == "__main__":
    asyncio.run(create_worker(WorkerSettings).main())
