import io
import os
import requests
import functools
from typing import Callable, Optional, BinaryIO, TYPE_CHECKING


class Reader(io.IOBase):
    size: Optional[int]

    def __init__(self, stream: BinaryIO, size: Optional[int], func_read: Optional[Callable[[int], bytes]] = None):
        self.size = size

        self.read = func_read or stream.read  # type: ignore
        for func in ('readable', 'seek', 'seekable', 'tell'):
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
        super().__init__(
            response.raw,
            response.raw.length_remaining if 'content-encoding' not in response.headers else None,
            func_read=functools.partial(response.raw.read, decode_content=True)
        )
