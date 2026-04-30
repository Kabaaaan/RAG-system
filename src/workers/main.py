import asyncio
import logging

from .generate_worker import run as run_generate
from .index_worker import run as run_index

logger = logging.getLogger(__name__)


async def run_all_workers() -> None:
    try:
        await asyncio.gather(run_generate(), run_index())
    except Exception:
        logger.exception("A worker crashed; shutting down")
        raise


if __name__ == "__main__":
    asyncio.run(run_all_workers())
