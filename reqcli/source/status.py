import requests
from enum import Enum

from ..errors import ResponseStatusError


class StatusCheckMode(Enum):
    NONE, CHECK_ERROR, REQUIRE_200 = range(3)

    def check(self, obj: requests.Response) -> None:
        if self is StatusCheckMode.NONE:
            pass
        elif self in (StatusCheckMode.CHECK_ERROR, StatusCheckMode.REQUIRE_200):
            status = obj.status_code

            # simple error check
            if status >= 400:
                raise ResponseStatusError(f'got status code {status} for url {obj.url}', status=status)
            # more restrictive check for status code 200
            if self is StatusCheckMode.REQUIRE_200 and status != 200:
                raise ResponseStatusError(f'expected status code 200, got {status} for url {obj.url}', status=status)
        else:
            assert False  # should never happen
