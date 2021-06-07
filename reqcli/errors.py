class ResponseStatusError(Exception):
    status: int

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status

    def __reduce__(self):  # pragma: no cover
        return (type(self), (*self.args, self.status))


class ConfigDependencyError(Exception):
    pass


class XmlLoadError(Exception):
    pass


class XmlSchemaError(Exception):
    pass


class ReaderError(Exception):
    pass


class TypeAlreadyLoadedError(Exception):
    pass
