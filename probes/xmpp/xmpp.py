from typing import Optional

import sentry_sdk
import slixmpp
from slixmpp import ClientXMPP
from .config import Config


class TracedClient(ClientXMPP):
    def __init__(self, jid: str, password: str, starttls: bool, remote: Optional[str]):
        super().__init__(jid, password)
        self.starttls = starttls
        self.remote = remote
        if self.remote:
            self.register_plugin('xep_0199')
        self.spans = []
        self.named_spans = {}
        self.add_event_handler('session_start', self.started, disposable=True)
        self.add_event_handler('message', self.message)
        self.add_event_handler('presence_available', self.presence)
        self.add_event_handler('connected', self.connected, disposable=True)
        self.add_event_handler('connection_failed', self.failure, disposable=True)
        self.add_event_handler('failed_auth', self.failure, disposable=True)
        self.add_event_handler('tls_success', self.tls, disposable=True)
        self.add_event_handler('auth_success', self.sasl, disposable=True)
        self.add_event_handler('session_bind', self.bind, disposable=True)
        self.spans.append(sentry_sdk.start_span(op='xmpp.session', description=jid))
        self.spans.append(self.spans[-1].start_child(op='session_start', description=jid))
        self.named_span('connect')

    async def failure(self, event):
        print("Failure", repr(event))
        await self.disconnect()

    def connected(self, event):
        self.clear_span_maybe('connect')
        if self.starttls:
            self.named_span('tls')
        else:
            self.named_span('sasl')

    def tls(self, event):
        self.clear_span_maybe('tls')
        self.named_span('sasl')

    def sasl(self, event):
        self.clear_span_maybe('sasl')
        self.named_span('bind')

    def bind(self, event):
        self.clear_span_maybe('bind')

    def named_span(self, name: str):
        current = self.spans[-1]
        self.named_spans[name] = current.start_child(op=name)

    def clear_span_maybe(self, which: str):
        span = self.named_spans.get(which)
        if span:
            span.finish()
            del self.named_spans[which]

    def clear_spans(self):
        for span in self.named_spans.values():
            span.finish()
        self.named_spans = {}
        while len(self.spans):
            span = self.spans.pop()
            span.finish()

    async def started(self, event):
        span = self.spans.pop()
        span.finish()
        self.named_span('presence')
        self.send_presence()
        with self.spans[-1].start_child(op='roster'):
            await self.get_roster()
        self.named_span('message')
        self.send_message(self.boundjid, 'Test')

    async def message(self, msg: slixmpp.Message):
        if msg.get_from() != self.boundjid:
            return
        self.clear_span_maybe('message')
        if self.remote:
            with self.spans[-1].start_child(op='ping'):
                await self.plugin['xep_0199'].ping(jid=self.remote)
        with self.spans[-1].start_child(op='disconnect'):
            await self.disconnect()

    async def presence(self, presence: slixmpp.Presence):
        if presence.get_from() != self.boundjid:
            return
        self.clear_span_maybe('presence')


async def probe(config: Config):
    print(config.title)
    xmpp = TracedClient(config.jid, config.password, config.starttls, config.remote)
    address = None
    if config.address:
        address = (config.address, config.port)
    xmpp.connect(use_ssl=not config.starttls, force_starttls=config.starttls, address=address)
    await xmpp.disconnected
    await xmpp.disconnect(wait=0.1, ignore_send_queue=True)
    xmpp.clear_spans()
