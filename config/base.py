import importlib
import yaml
from pydantic import BaseModel


class SentryConfig(BaseModel):
    dsn: str
    tags: dict[str,str]


class ProbeConfig(BaseModel):
    probe: str
    every: int = 300
    burst: int = 1
    tags: dict[str,str] = {}


class ProbeGroup(BaseModel):
    tags: dict[str,str] = {}
    probes: list[dict]


class Config(BaseModel):
    sentry: SentryConfig
    groups: list[ProbeGroup]
    tags: dict[str,str] = {}


def load(filename: str):
    config_raw = dict()

    with open(filename, "r") as stream:
        try:
            config_raw = yaml.safe_load(stream)
        except yaml.YAMLError as err:
            print(err)

    return Config(**config_raw)


def check(config: dict[str,str], group: ProbeGroup):
    base_config = ProbeConfig(**config)
    probe = importlib.import_module(base_config.probe)
    return probe.check_config(config, group)
