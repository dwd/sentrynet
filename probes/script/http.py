from http_utils import ProbeRequest, traced_session, traced_request, interpolate
from .config import Config


async def probe(config: Config):
    keys = {}
    if config.init_keys is not None:
        keys.update(config.init_keys)
    async with traced_session() as session:
        for step in config.steps:
            request = ProbeRequest(
                url=interpolate(step.url, keys),
                method=step.method,
                expected=step.expected,
                set_keys=step.set_keys,
                assertions=step.assertions,
                body=interpolate(step.body, keys)
            )
            new_keys = await traced_request(session, request)
            keys.update(new_keys)
