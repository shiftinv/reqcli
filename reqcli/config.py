from typing import Type
from requests_cache.backends import BackendSpecifier

from .type.config import TypeLoadConfig


class Configuration:
    cache_backend: BackendSpecifier = 'sqlite'
    cache_name: str = './cache/requests.db'
    default_user_agent: str = ''
    type_load_config_type: Type[TypeLoadConfig] = TypeLoadConfig

    def __init__(self):
        raise AssertionError
