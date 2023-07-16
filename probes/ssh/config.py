from typing import Optional
from pydantic import BaseModel
from config.base import ProbeGroup, ProbeConfig
from urllib.parse import urlparse


class Config(ProbeConfig):
    host: str
    username: str
    port: int = 22
    identity: Optional[str] = None
    command: Optional[str] = None


def check_config(config: dict, group: ProbeGroup):
    conf = Config(**config)
    conf.tags.update(group.tags)
    if not conf.title:
        conf.title = 'SSH %s@%s:%s' % (conf.username, conf.host, conf.port)
    return conf
