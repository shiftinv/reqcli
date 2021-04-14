import contextlib

from . import basesource
from .reqdata import ReqData


class UnloadableType:
    def __init__(self, source: 'basesource.BaseSource', reqdata: ReqData, skip_store_to_cache: bool):
        self.source = source
        self.reqdata = reqdata
        self.skip_store_to_cache = skip_store_to_cache

    @contextlib.contextmanager
    def get_reader(self):
        with self.source.get_reader(self.reqdata, skip_store_to_cache=self.skip_store_to_cache) as reader:
            yield reader
