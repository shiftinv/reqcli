import contextlib
from typing import Any, Dict, Iterator

from . import basesource
from .reqdata import ReqData
from .. import reader


class UnloadableType:
    def __init__(self, source: 'basesource.BaseSource', reqdata: ReqData, kwargs: Dict[str, Any]):
        self.source = source
        self.reqdata = reqdata
        self.kwargs = kwargs

    @contextlib.contextmanager
    def get_reader(self) -> Iterator[reader.ResponseReader]:
        with self.source.get_reader(self.reqdata, **self.kwargs) as reader:
            yield reader
