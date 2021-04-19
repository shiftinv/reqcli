from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class TypeLoadConfig:
    construct_kwargs: Dict[str, Any] = field(default_factory=lambda: {})
