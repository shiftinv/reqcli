import io
import os
import requests
import functools
from typing import Optional, BinaryIO, TYPE_CHECKING

from .errors import ReaderError


class Reader(io.BufferedReader):
    size: Optional[int]

    def __init__(self, stream: BinaryIO, size: Optional[int]):
        self.size = size

        for func in ('read', 'readable', 'seek', 'seekable', 'tell'):
            # only copy if function does not exist yet or is default value
            existing_func = getattr(self, func, None)
            if existing_func is None or existing_func == getattr(super(), func, None):
                setattr(self, func, getattr(stream, func))

    # :/
    if TYPE_CHECKING:
        def read(self, n: Optional[int] = None) -> bytes:
            ...


class IOReader(Reader):
    def __init__(self, io: BinaryIO):
        orig_offset = io.tell()
        size = io.seek(0, os.SEEK_END)
        io.seek(orig_offset, os.SEEK_SET)

        super().__init__(io, size)


class ResponseReader(Reader):
    def __init__(self, response: requests.Response):
        if response.raw.isclosed():
            raise ReaderError('response stream is already closed; ResponseReader requires `stream=True`')

        size: Optional[int]
        if 'content-length' in response.headers and 'content-encoding' not in response.headers:
            size = int(response.headers['content-length'])
        else:
            size = None

        super().__init__(
            response.raw,
            size
        )

        self.__read = functools.partial(response.raw.read, decode_content=True)

        assert response.raw.tell() == 0
        self._read_bytes = 0

    def tell(self) -> int:
        # note: no need to consider calls to seek(), since responses are not seekable
        return self._read_bytes

    def read(self, n: Optional[int] = None) -> bytes:
        data = self.__read(n)
        self._read_bytes += len(data)
        return data
