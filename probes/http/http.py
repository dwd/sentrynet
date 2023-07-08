import aiohttp
import sentry_sdk
from .config import Config


class ProbeException(Exception):
    def __init__(self, status):
        super().__init__(status)


class TraceContext:
    transaction: sentry_sdk.tracing.Transaction
    spans: list[sentry_sdk.tracing.Span]
    recv: bool
    trace_request_ctx: Config


async def request_start(session, trace_context: TraceContext, params: aiohttp.TraceRequestStartParams):
    print("START")
    trace_context.transaction = sentry_sdk.start_transaction(op='http.probe', name='%s %s' % (params.method, params.url))
    config = trace_context.trace_request_ctx
    for tag, value in config.tags.items():
        trace_context.transaction.set_tag(tag, value)
    trace_context.spans = []
    trace_context.spans.append(trace_context.transaction.start_child(op='http.request', description='%s %s' % (params.method, params.url)))
    trace_context.recv = False


async def request_end(session, trace_context: TraceContext, params: aiohttp.TraceRequestEndParams):
    print("END")
    while len(trace_context.spans):
        span = trace_context.spans.pop()
        span.set_http_status(params.response.status)
        span.finish()
    trace_context.transaction.set_http_status(params.response.status)
    trace_context.transaction.finish()


async def gen_end(multi = 1):
    async def end(session, trace_context: TraceContext, params):
        for i in range(multi):
            span = trace_context.spans.pop()
            print("Ending span", span.op)
            span.finish()


def gen_start(op, name):
    async def start(session, trace_context: TraceContext, params: aiohttp.TraceConnectionCreateStartParams):
        current = trace_context.spans[-1]
        trace_context.spans.append(current.start_child(op=op, description=name))
        print("Starting span", op)
    return start


def gen_switch(op, name, multi=1):
    async def start(session, trace_context: TraceContext, params: aiohttp.TraceConnectionCreateStartParams):
        for i in range(multi):
            span = trace_context.spans.pop()
            print("Switching out of span", span.op)
            span.finish()
        current = trace_context.spans[-1]
        trace_context.spans.append(current.start_child(op=op, description=name))
        print("Switching to span", op)
    return start


async def rx_chunk(session, trace_context: TraceContext, params: aiohttp.TraceConnectionCreateStartParams):
    print("RX chunk")
    if not trace_context.recv:
        trace_context.recv = True
        span = trace_context.spans.pop()
        span.finish()
        current = trace_context.spans[-1]

        trace_context.spans.append(current.start_child(op='http.recv', description='Receiving response'))


async def probe(config: Config):
    tracer = aiohttp.TraceConfig()
    tracer.on_request_start.append(request_start)
    tracer.on_request_end.append(request_end)
    tracer.on_connection_create_start.append(gen_start('net.conn', 'Creating connection'))
    tracer.on_dns_resolvehost_start.append(gen_start('net.dns', 'DNS resolution'))
    tracer.on_dns_resolvehost_end.append(gen_switch('net.tls', 'Connect and TLS'))
    tracer.on_connection_create_end.append(gen_switch('http.send', 'Send request', 2))
    tracer.on_request_headers_sent.append(gen_switch('http.wait', 'Awaiting response'))
    tracer.on_response_chunk_received.append(rx_chunk)

    async with aiohttp.ClientSession(trace_configs=[tracer]) as session:
        async with session.get(config.url, trace_request_ctx=config) as resp:
            if resp.status != config.expected:
                sentry_sdk.capture_message('GET %s returned %s' % (config.url, config.expected))
