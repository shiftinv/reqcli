import io
import os
import requests
import functools
from typing import Optional, BinaryIO, TYPE_CHECKING

from .errors import ReaderError


class Reader(io.IOBase):
    size: Optional[int]

    def __init__(self, stream: BinaryIO, size: Optional[int]):
        self.size = size

        for func in ('read', 'readable', 'seek', 'seekable', 'tell'):
            setattr(self, func, getattr(stream, func))

    # :/
    if TYPE_CHECKING:
        def read(self, n: int = -1) -> bytes:
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

        self.read = functools.partial(response.raw.read, decode_content=True)  # type: ignore
