import re
import time
import logging
import requests
import threading
import collections
import urllib.parse
import requests_cache
import requests_cache.backends
from typing import Dict, Any, cast


# suppress warnings about unrecognized arguments due to CachedRateLimitedSession
requests_cache.backends.base.logger.addFilter(lambda r: not re.match(r'Unrecognized keyword arguments: \{\'requests_per_second\': [^,]+\}', r.getMessage()))  # pragma: no cover

_logger = logging.getLogger(__name__)


class RateLimitingMixin:
    __last_call: Dict[str, float] = collections.defaultdict(lambda: 0)
    __lock = threading.RLock()

    def __init__(self, requests_per_second: float, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)  # type: ignore
        assert requests_per_second > 0
        self._ratelimit_interval = 1.0 / requests_per_second

    def send(self, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        if self._ratelimit_interval != 0:
            host = urllib.parse.urlparse(cast(str, request.url)).netloc
            wait_time = self.__get_wait_time(host)

            if wait_time > 0:
                _logger.info(f'Ratelimiting request to {host}, waiting {wait_time:.2f}s')
                time.sleep(wait_time)

        return super().send(request, **kwargs)  # type: ignore

    def __get_wait_time(self, key: str) -> float:
        cls = type(self)
        with cls.__lock:
            # calculate difference to previous call
            last_time = cls.__last_call[key]
            now = time.time()
            diff = now - last_time

            # calculate wait time, update last call time to (future) next call
            wait_time = max(0, self._ratelimit_interval - diff)
            cls.__last_call[key] = now + wait_time
            return wait_time


class RateLimitedSession(RateLimitingMixin, requests.Session):
    pass


class CachedRateLimitedSession(requests_cache.CacheMixin, RateLimitedSession):
    pass
