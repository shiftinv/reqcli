from dataclasses import dataclass

from .status import StatusCheckMode
from ..config import Configuration
from ..errors import ConfigDependencyError
from ..type import TypeLoadConfig


@dataclass(frozen=True)
class SourceConfig:
    load_from_cache: bool = True
    store_to_cache: bool = True
    store_metadata: bool = True
    store_failed_requests: bool = True
    chunk_size: int = Configuration.default_chunk_size  # note: with streamed requests, this value is the size of compressed chunks (i.e. the size of returned chunks may be larger)
    response_status_checking: StatusCheckMode = StatusCheckMode.REQUIRE_200
    http_retries: int = 3
    requests_per_second: float = 5.0
    type_load_config: TypeLoadConfig = TypeLoadConfig()

    def __post_init__(self):
        dependencies = {
            'store_metadata': 'store_to_cache',
            'store_failed_requests': 'store_metadata'
        }
        for key, dependency in dependencies.items():
            key_value = getattr(self, key)
            dependency_value = getattr(self, dependency)
            assert isinstance(key_value, bool) and isinstance(dependency_value, bool)
            if key_value and not dependency_value:
                raise ConfigDependencyError(f'configuration option {key!r} requires {dependency!r}')
