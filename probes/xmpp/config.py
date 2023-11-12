from config.base import ProbeGroup, ProbeConfig
from typing import Optional


class Config(ProbeConfig):
    jid: str
    password: str
    starttls: bool = False
    address: Optional[str] = None
    port: Optional[int] = None
    remote: Optional[str] = None


def check_config(config: dict, group: ProbeGroup):
    conf = Config(**config)
    conf.tags.update(group.tags)
    if not conf.title:
        xmpp = 'xmpps'
        if conf.starttls:
            xmpp = 'xmpp'
            conf.port = conf.port or 5222
        else:
            conf.port = conf.port or 5223
            if not conf.address:
                raise ValueError('Must supply address if not using StartTLS')
        conf.title = '%s://%s' % (xmpp, conf.jid)
    return conf
