from typing import Optional
from pydantic import BaseModel
from config.base import ProbeGroup, ProbeConfig
from urllib.parse import urlparse


class Step(BaseModel):
    url: str
    method: Optional[str] = None
    query: dict[str,str] = {}
    body: Optional[dict[str,str]] = None
    expected: int = 200


class Config(ProbeConfig):
    steps: list[Step]


def check_config(config: dict, group: ProbeGroup):
    conf = Config(**config)
    conf.tags.update(group.tags)
    if not conf.title:
        url = urlparse(conf.url)
        conf.title = 'GET %s://%s' % (url.scheme, url.netloc)
    return conf
