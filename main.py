import asyncio
import importlib

import sentry_sdk

from config.base import ProbeConfig, ProbeGroup
from config import load, check


async def probe_single(probe, config: ProbeConfig):
    with sentry_sdk.Hub(sentry_sdk.Hub.current) as hub:
        with hub.push_scope() as scope:
            with hub.start_transaction(op=config.probe, name=config.title) as transaction:
                try:
                    scope.span = transaction
                    scope.set_tag('probe', config.probe)
                    for tag, val in config.tags.items():
                        scope.set_tag(tag, val)
                    await probe.probe(config)
                    transaction.set_status('ok')
                except Exception as err:
                    print("Transaction: %s error: %s" % (transaction.name, str(err)))
                    transaction.set_status('internal_error')
                    hub.capture_exception(err)


async def probe_every(config: ProbeConfig):
    probe = importlib.import_module(config.probe)
    while True:
        for i in range(config.burst):
            await probe_single(probe, config)
        await asyncio.sleep(config.every)


def probe_group(group: ProbeGroup):
    probe_tasks = []
    for probe in group.probes:
        probe_config = check(probe, group)
        probe_tasks.append(asyncio.create_task(probe_every(probe_config)))
    return probe_tasks


async def main():
    import sentry_sdk
    import sys
    import logging

    logging.basicConfig(level=logging.DEBUG)

    config = load(sys.argv[1])

    sentry_sdk.init(
        dsn=config.sentry.dsn,
        traces_sample_rate=1.0
    )

    probe_tasks = []
    for group in config.groups:
        probe_tasks += probe_group(group)
    await asyncio.wait(probe_tasks)

asyncio.run(main())
