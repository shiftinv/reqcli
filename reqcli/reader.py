import os
import json
import time
import requests
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Callable, Iterable, Iterator, Optional, Dict, List, BinaryIO, Type

from .utils import misc


@dataclass(frozen=True)
class Metadata:
    http_version: str
    status: int
    status_reason: str
    response_headers: Dict[str, List[str]]
    url: str
    timestamp: int
    elapsed_ms: int

    def write_file(self, path: str) -> None:
        with open(path, 'w') as f:
            return json.dump(asdict(self), f)

    @classmethod
    def from_file(cls, path: str) -> 'Metadata':
        with open(path, 'r') as f:
            return cls(**json.load(f))

    @classmethod
    def from_response(cls, response: requests.Response) -> 'Metadata':
        headers = response.raw.headers
        return cls(
            http_version={9: '0.9', 10: '1.0', 11: '1.1'}[response.raw.version],
            status=response.status_code,
            status_reason=response.reason,
            response_headers={k: headers.getlist(k) for k in headers},
            url=response.url,
            timestamp=int(time.time()),
            elapsed_ms=int(response.elapsed.total_seconds() * 1000)
        )


class Reader(Iterator[bytes], ABC):
    size: Optional[int]  # *compressed* size (for HTTP responses), see `SourceConfig.chunk_size`
    metadata: Optional[Metadata]

    def __init__(self, size: Optional[int], meta: Optional[Metadata]):
        self.size = size
        self.metadata = meta

    def read_all(self) -> bytes:
        return b''.join(self)

    @abstractmethod
    def __next__(self):
        pass

    @property
    @abstractmethod
    def current_offset(self) -> int:
        # offset in *compressed* data (for HTTP responses), see `SourceConfig.chunk_size`
        pass


class _FuncReader(Reader):
    def __init__(self, size: Optional[int], meta: Optional[Metadata], func_read: Callable[[], bytes], func_get_offset: Callable[[], int]):
        super().__init__(size, meta)
        self.__func_read = func_read
        self.__func_get_offset = func_get_offset

    def __next__(self):
        data = self.__func_read()
        if data == b'':
            raise StopIteration
        return data

    @property
    def current_offset(self) -> int:
        # *compressed* size (for HTTP responses), see `SourceConfig.chunk_size`
        return self.__func_get_offset()


class ResponseReader(_FuncReader):
    def __init__(self, response: requests.Response, chunk_size: int, meta: Optional[Metadata]):
        res_it = response.iter_content(chunk_size)
        super().__init__(
            response.raw.length_remaining,
            meta,
            lambda: next(res_it),
            response.raw.tell
        )


class IOReader(_FuncReader):
    def __init__(self, io: BinaryIO, chunk_size: int, meta: Optional[Metadata]):
        orig_offset = io.tell()
        size = io.seek(0, os.SEEK_END)
        io.seek(orig_offset, os.SEEK_SET)

        super().__init__(
            size,
            meta,
            lambda: io.read(chunk_size),
            io.tell
        )


class CachingReader(Reader):
    def __init__(self, subreader: Reader, filename: str, store_on_errors: Iterable[Type[Exception]] = tuple()):
        super().__init__(
            subreader.size,
            subreader.metadata
        )

        self._subreader = subreader
        self.filename = filename
        self._store_on_errors = set(store_on_errors)

        self._tmp_filename = f'{filename}.tmp'
        self.__file = None  # type: Optional[BinaryIO]

    def __next__(self):
        data = next(self._subreader)
        if self.__file is None:
            raise RuntimeError('cache file wasn\'t opened')
        self.__file.write(data)
        return data

    @property
    def current_offset(self) -> int:
        return self._subreader.current_offset

    def __enter__(self):
        misc.create_dirs_for_file(self._tmp_filename)
        assert self.__file is None
        self.__file = open(self._tmp_filename, 'wb')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.__file is None:
            # tmp file wasn't created yet, nothing to clean up/write
            return

        write_file = (exc_type is None) or (exc_type in self._store_on_errors)
        if write_file:
            # finish writing in case not everything was read
            for _ in self:
                pass
        self.__file.close()
        self.__file = None

        # move tmp file if successful
        if write_file:
            os.replace(self._tmp_filename, self.filename)
        else:
            os.unlink(self._tmp_filename)
