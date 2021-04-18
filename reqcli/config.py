from dataclasses import dataclass
from requests_cache.backends import BackendSpecifier


@dataclass
class _Configuration:
    cache_backend: BackendSpecifier = 'sqlite'
    cache_name: str = './cache/requests.db'
    default_user_agent: str = ''


Configuration = _Configuration()
