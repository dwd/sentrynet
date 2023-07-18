import json
import aiohttp
import sentry_sdk
from http_utils import ProbeRequest


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


async def traced_request(session, request: ProbeRequest):
    transaction = sentry_sdk.Hub.current.scope.transaction
    headers = {key: value for key, value in transaction.iter_headers()}
    method = request.method
    if request.method is None:
        if request.body is not None:
            method = 'POST'
        else:
            method = 'GET'
    body = request.body
    if body is not None:
        if not isinstance(body, (str, bytes)):
            headers['content-type'] = 'application/json'
            body = json.dumps(body)
    expected = request.expected
    if expected is None:
        if method == 'POST':
            expected = 201
        else:
            expected = 200
    print("{method} {url} {body}".format(method=method, url=request.url, body=body))
    async with session.request(method, request.url, headers=headers, data=body) as resp:
        # sentry_sdk.set_measurement('response_size', resp.content_length, 'byte')
        if resp.status != expected:
            raise ValueError('%s %s returning %s, expected %s' % (method, request.url, resp.status, expected))
        data = await resp.text()
        if request.set_keys is not None:
            returned_keys = {}
            with sentry_sdk.Hub.current.scope.span.start_child(op='json.parse', description='Parse body'):
                json_response = json.loads(data)
                for key, path in request.set_keys.items():
                    match = path.find(json_response)
                    if len(match) == 1:
                        returned_keys[key] = match[0].value
                    elif len(match) > 1:
                        returned_keys[key] = [m.value for m in match]
            if request.assertions is not None:
                with sentry_sdk.Hub.current.scope.span.start_child(op='json.assert', description='Checking assertions'):
                    for key, assertion in request.assertions.items():
                        if assertion.exists:
                            if key not in returned_keys:
                                raise KeyError(f'Key {key} not found in response')
                            if assertion.value:
                                if returned_keys[key] != assertion.value:
                                    raise ValueError(f'Key {key} is {returned_keys[key]}, not {assertion.value}')
                        else:
                            if key in returned_keys:
                                raise KeyError(f'Key {key} unexpectedly set')
            return returned_keys
        return data
