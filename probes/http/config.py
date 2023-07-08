import pydantic
from config.base import ProbeGroup, ProbeConfig


class Config(ProbeConfig):
    url: str
    expected: int = 200
    tags: dict[str,str] = {}


def check_config(config: dict, group: ProbeGroup):
    conf = Config(**config)
    conf.tags.update(group.tags)
    return conf
