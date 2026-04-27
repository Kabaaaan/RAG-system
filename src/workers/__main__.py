from __future__ import annotations

import asyncio

from .main import run_all_workers

if __name__ == "__main__":
    asyncio.run(run_all_workers())
