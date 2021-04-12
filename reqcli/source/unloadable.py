import contextlib

from . import basesource
from .reqdata import ReqData


class UnloadableType:
    def __init__(self, source: 'basesource.BaseSource', reqdata: ReqData):
        self.source = source
        self.reqdata = reqdata

    @contextlib.contextmanager
    def get_reader(self):
        with self.source.get_reader(self.reqdata) as reader:
            yield reader
