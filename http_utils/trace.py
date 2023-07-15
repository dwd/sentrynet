import json
import aiohttp
import sentry_sdk


class ProbeException(Exception):
    def __init__(self, status):
        super().__init__(status)


class TraceContext:
    spans: list[sentry_sdk.tracing.Span]
    recv: bool


async def request_start(session, trace_context: TraceContext, params: aiohttp.TraceRequestStartParams):
    trace_context.spans = [sentry_sdk.start_span(op='http.request', description='%s %s' % (params.method, params.url))]
    trace_context.recv = False


async def request_end(session, trace_context: TraceContext, params: aiohttp.TraceRequestEndParams):
    while len(trace_context.spans):
        span = trace_context.spans.pop()
        span.set_http_status(params.response.status)
        span.finish()


async def gen_end(multi = 1):
    async def end(session, trace_context: TraceContext, params):
        for i in range(multi):
            span = trace_context.spans.pop()
            span.finish()


def gen_start(op, name):
    async def start(session, trace_context: TraceContext, params: aiohttp.TraceConnectionCreateStartParams):
        current = trace_context.spans[-1]
        trace_context.spans.append(current.start_child(op=op, description=name))
    return start


def gen_switch(op, name, multi=1):
    async def start(session, trace_context: TraceContext, params: aiohttp.TraceConnectionCreateStartParams):
        for i in range(multi):
            span = trace_context.spans.pop()
            span.finish()
        current = trace_context.spans[-1]
        trace_context.spans.append(current.start_child(op=op, description=name))
    return start


async def rx_chunk(session, trace_context: TraceContext, params: aiohttp.TraceConnectionCreateStartParams):
    if not trace_context.recv:
        trace_context.recv = True
        span = trace_context.spans.pop()
        span.finish()
        current = trace_context.spans[-1]

        trace_context.spans.append(current.start_child(op='http.recv', description='Receiving response'))


def traced_session():
    tracer = aiohttp.TraceConfig()
    tracer.on_request_start.append(request_start)
    tracer.on_request_end.append(request_end)
    tracer.on_connection_create_start.append(gen_start('net.conn', 'Creating connection'))
    tracer.on_dns_resolvehost_start.append(gen_start('net.dns', 'DNS resolution'))
    tracer.on_dns_resolvehost_end.append(gen_switch('net.tls', 'Connect and TLS'))
    tracer.on_connection_create_end.append(gen_switch('http.send', 'Send request', 2))
    tracer.on_request_headers_sent.append(gen_switch('http.wait', 'Awaiting response'))
    # tracer.on_response_chunk_received.append(rx_chunk)

    return aiohttp.ClientSession(trace_configs=[tracer])


async def traced_request(session, url: str, method: str = None, body: dict = None, expected: int = None):
    transaction = sentry_sdk.Hub.current.scope.transaction
    headers = {key: value for key, value in transaction.iter_headers()}
    if method is None:
        if body is not None:
            method = 'POST'
        else:
            method = 'GET'
    if body is not None:
        body = json.dumps(body)
    if expected is None:
        if method == 'POST':
            expected = 201
        else:
            expected = 200
    print("{method} {url} {body}".format(method=method, url=url, body=body))
    async with session.request(method, url, headers=headers, data=body) as resp:
        # sentry_sdk.set_measurement('response_size', resp.content_length, 'byte')
        if resp.status != expected:
            raise ValueError('%s %s returning %s, expected %s' % (method, url, resp.status, expected))
        data = await resp.text()
        return data
