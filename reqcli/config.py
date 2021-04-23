from dataclasses import dataclass
from typing import Type
from requests_cache.backends import BackendSpecifier

from .type import TypeLoadConfig


@dataclass
class _Configuration:
    cache_backend: BackendSpecifier = 'sqlite'
    cache_name: str = './cache/requests.db'
    default_user_agent: str = ''
    type_load_config_type: Type[TypeLoadConfig] = TypeLoadConfig


Configuration = _Configuration()
