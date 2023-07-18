from http_utils import traced_session, traced_request, ProbeRequest
from .config import Config

async def probe(step: Config):
    async with traced_session() as session:
        request = ProbeRequest(
            url=step.url,
            method=step.method,
            expected=step.expected,
            set_keys=step.set_keys,
            assertions=step.assertions,
            body=step.body,
        )
        await traced_request(session, request)
