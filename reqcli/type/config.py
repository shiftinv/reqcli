from dataclasses import dataclass


@dataclass(frozen=True)
class TypeLoadConfig:
    verify_checksums: bool = True
