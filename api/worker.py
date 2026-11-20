"""ARQ worker entry-point.

Usage:
    uv run python -m api.worker
"""

import asyncio

from arq.worker import create_worker

from api.workers.simulation_worker import WorkerSettings

if __name__ == "__main__":
    # WorkerSettings is a plain settings class, as ARQ documents; its stubs want a Protocol.
    asyncio.run(create_worker(WorkerSettings).main())  # type: ignore[arg-type]
