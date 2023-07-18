from typing import Optional
from config.base import ProbeGroup, ProbeConfig
from urllib.parse import urlparse
from http_utils import Assertion


## Essentially a ProbeRequest that's inherited from ProbeConfig.
class Config(ProbeConfig):
    url: str
    method: Optional[str] = None
    query: dict = {}
    body: Optional[dict] = None
    expected: int = 200
    set_keys: Optional[dict] = None
    assertions: Optional[dict[str,Assertion]] = None


def check_config(config: dict, group: ProbeGroup):
    conf = Config(**config)
    conf.tags.update(group.tags)
    if not conf.title:
        url = urlparse(conf.url)
        conf.title = '%s %s://%s' % (conf.method or 'GET', url.scheme, url.netloc)
    return conf
