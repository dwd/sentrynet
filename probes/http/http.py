import sentry_sdk

from http_utils.trace import traced_session, traced_request
from .config import Config

async def probe(config: Config):
    async with traced_session() as session:
        transaction = sentry_sdk.Hub.current.scope.transaction
        headers = {key: value for key, value in transaction.iter_headers()}
        response = await traced_request(session, config.url, method=config.method, expected=config.expected)
