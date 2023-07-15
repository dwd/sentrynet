from config.base import ProbeGroup, ProbeConfig
from urllib.parse import urlparse


class Config(ProbeConfig):
    url: str
    expected: int = 200
    tags: dict[str,str] = {}


def check_config(config: dict, group: ProbeGroup):
    conf = Config(**config)
    conf.tags.update(group.tags)
    if not conf.title:
        url = urlparse(conf.url)
        conf.title = 'GET %s://%s' % (url.scheme, url.netloc)
    return conf
