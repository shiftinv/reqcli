import io
import lxml.objectify
from abc import ABC, abstractmethod
from construct import Construct
from typing import Optional, Tuple, Type, TypeVar, Dict, Any, BinaryIO

from .config import TypeLoadConfig
from .. import reader, utils


# currently does nothing, but having it could be useful in the future
class BaseType:
    pass


_T = TypeVar('_T', bound='BaseTypeLoadable')


class BaseTypeLoadable(BaseType, ABC):
    def __init__(self):
        super().__init__()
        self.__loaded = False

    def load_file(self: _T, filename: str, config: Optional[TypeLoadConfig] = None) -> _T:
        with open(filename, 'rb') as f:
            return self.load_stream(f, config)

    def load_bytes(self: _T, data: bytes, config: Optional[TypeLoadConfig] = None) -> _T:
        return self.load_stream(io.BytesIO(data), config)

    def load_stream(self: _T, stream: BinaryIO, config: Optional[TypeLoadConfig] = None) -> _T:
        return self.load(reader.IOReader(stream), config)

    def load(self: _T, reader: reader.Reader, config: Optional[TypeLoadConfig] = None) -> _T:
        if self.__loaded:
            raise RuntimeError('instance is already loaded')
        if not config:
            config = TypeLoadConfig()  # use default config if none provided

        self._read(reader, config)
        self.__loaded = True

        return self

    @abstractmethod
    def _read(self, reader: reader.Reader, config: TypeLoadConfig) -> None:
        pass


class BaseTypeLoadableConstruct(BaseTypeLoadable):
    def __init__(self, struct: Construct):
        super().__init__()
        self.__struct = struct

    def _parse_construct(self, data: bytes, config: TypeLoadConfig) -> Construct:
        return self.__struct.parse(
            data,
            skip_verify_checksums=not config.verify_checksums
        )


_TXml = TypeVar('_TXml', bound='XmlBaseType')


class XmlBaseType(ABC):
    @classmethod
    @abstractmethod
    def _parse_internal(cls: Type[_TXml], xml: lxml.objectify.ObjectifiedElement) -> Dict[str, Any]:
        pass

    @classmethod
    def _get_schema(cls) -> Optional[Tuple[utils.xml.SchemaType, bool]]:
        return None

    @classmethod
    def _parse(cls: Type[_TXml], xml: lxml.objectify.ObjectifiedElement) -> _TXml:
        schema_tup = cls._get_schema()
        if schema_tup is not None:
            schema, superset = schema_tup
            utils.xml.validate_schema(xml, schema, superset)

        return cls(**cls._parse_internal(xml))  # type: ignore  # https://github.com/python/mypy/issues/5374
