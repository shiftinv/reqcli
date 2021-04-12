from dataclasses import dataclass


@dataclass
class _Configuration:
    cache_path: str = './cache/'
    default_user_agent: str = ''
    default_chunk_size: int = 32768


Configuration = _Configuration()
