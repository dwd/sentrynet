from typing import Optional
from config.base import ProbeGroup, ProbeConfig
from urllib.parse import urlparse


class Config(ProbeConfig):
    url: str
    method: Optional[str] = None
    expected: Optional[int] = None
    tags: dict[str,str] = {}


def check_config(config: dict, group: ProbeGroup):
    conf = Config(**config)
    conf.tags.update(group.tags)
    if not conf.title:
        url = urlparse(conf.url)
        conf.title = '%s %s://%s' % (conf.method or 'GET', url.scheme, url.netloc)
    return conf
