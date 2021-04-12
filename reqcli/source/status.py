import requests
from enum import Enum
from typing import Union

from .. import reader
from ..errors import ResponseStatusError


class StatusCheckMode(Enum):
    NONE, CHECK_ERROR, REQUIRE_200 = range(3)

    def check(self, obj: Union[requests.Response, reader.Metadata]) -> None:
        if self is StatusCheckMode.NONE:
            pass
        elif self in (StatusCheckMode.CHECK_ERROR, StatusCheckMode.REQUIRE_200):
            if isinstance(obj, requests.Response):
                status = obj.status_code
            else:
                status = obj.status

            # simple error check
            if status >= 400:
                raise ResponseStatusError(f'got status code {status} for url {obj.url}', status=status)
            # more restrictive check for status code 200
            if self is StatusCheckMode.REQUIRE_200 and status != 200:
                raise ResponseStatusError(f'expected status code 200, got {status} for url {obj.url}', status=status)
        else:
            assert False  # should never happen
