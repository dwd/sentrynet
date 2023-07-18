from typing import Optional
from config.base import ProbeGroup, ProbeConfig
from http_utils import ProbeRequest
import jsonpath_ng


class Config(ProbeConfig):
    init_keys: Optional[dict] = None
    steps: list[ProbeRequest]


def check_config(config: dict, group: ProbeGroup):
    conf = Config(**config)
    conf.tags.update(group.tags)
    if not conf.title:
        conf.title = 'Un-named script'
        raise KeyError('Scripts must have an explicit title')
    for s in conf.steps:
        if s.set_keys is not None:
            sk = {}
            for key,path_str in s.set_keys.items():
                sk[key] = jsonpath_ng.parse(path_str)
            s.set_keys = sk
    return conf
