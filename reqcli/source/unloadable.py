import contextlib
from typing import Iterator

from . import basesource
from .reqdata import ReqData
from .. import reader


class UnloadableType:
    def __init__(self, source: 'basesource.BaseSource', reqdata: ReqData, skip_cache: bool):
        self.source = source
        self.reqdata = reqdata
        self.skip_cache = skip_cache

    @contextlib.contextmanager
    def get_reader(self) -> Iterator[reader.Reader]:
        with self.source.get_reader(self.reqdata, skip_cache=self.skip_cache) as reader:
            yield reader
