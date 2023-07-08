# This is a sample Python script.
import asyncio
from datetime import datetime, timedelta
import importlib
from typing import Optional

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

from config.base import ProbeConfig


async def probe_every(config: ProbeConfig):
    print("Trying to probe using", repr(config))
    probe = importlib.import_module(config.probe)
    while True:
        for i in range(config.burst):
            await probe.probe(config)
        await asyncio.sleep(config.every)


async def main():
    import sentry_sdk
    from config import load, check
    import sys

    config = load(sys.argv[1])

    sentry_sdk.init(
        dsn=config.sentry.dsn,
        traces_sample_rate=1.0
    )

    probe_tasks = []
    for group in config.groups:
        for probe in group.probes:
            probe_config = check(probe, group)
            probe_tasks.append(asyncio.create_task(probe_every(probe_config)))
    await asyncio.wait(probe_tasks)

asyncio.run(main())
