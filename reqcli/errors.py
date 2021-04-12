class ResponseStatusError(Exception):
    status: int

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


class ConfigDependencyError(Exception):
    pass
