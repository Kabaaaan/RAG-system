import asyncio

from .generate_worker import run as run_generate
from .index_worker import run as run_index


async def run_all_workers():
    await asyncio.gather(run_generate(), run_index(), return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(run_all_workers())
