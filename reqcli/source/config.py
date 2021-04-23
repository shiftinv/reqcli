from dataclasses import dataclass, field
from typing import Iterable

from .status import StatusCheckMode
from ..type import TypeLoadConfig
from ..config import Configuration


@dataclass(frozen=True)
class SourceConfig:
    enable_cache: bool = True
    cache_response_codes: Iterable[int] = frozenset({200, 204, 301, 302, 303, 304, 307, 308, 401, 403, 404})
    response_status_checking: StatusCheckMode = StatusCheckMode.REQUIRE_200
    http_retries: int = 3
    requests_per_second: float = 5.0
    type_load_config: TypeLoadConfig = field(default_factory=lambda: Configuration.type_load_config_type())
