import json

import aiohttp
import sentry_sdk
from urllib.parse import urlparse

from http_utils.trace import traced_session, traced_request
from .config import Config


async def probe(config: Config):
    async with traced_session() as session:
        for step in config.steps:
            data = await traced_request(session, step.url, method=method, body=step.body)
            print(repr(data))
