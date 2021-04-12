import time
import threading
import functools
import collections
from typing import Dict, Type, Union, Callable, Any, cast

from ..utils.typing import TFuncAny


class limit:
    _last_call: Dict[Type[Any], float] = collections.defaultdict(lambda: 0)
    _lock = threading.RLock()

    def __init__(self, calls_per_second: Union[Callable[[Any], float], float] = 1.0):
        self._calls_per_second = calls_per_second

    def __call__(self, func: TFuncAny) -> TFuncAny:
        @functools.wraps(func)
        def wrapper(self_inner, *args, **kwargs):
            self._setup_interval(self_inner)
            wait_time = self._get_wait_time(type(self_inner))

            if wait_time > 0:
                time.sleep(wait_time)

            return func(self_inner, *args, **kwargs)
        return cast(TFuncAny, wrapper)

    def _get_wait_time(self, key: Type[Any]) -> float:
        with self._lock:
            # calculate difference to previous call
            last_time = self._last_call[key]
            now = time.time()
            diff = now - last_time

            # calculate wait time, update last call time to (future) next call
            wait_time = max(0, self.interval - diff)
            self._last_call[key] = now + wait_time
            return wait_time

    def _setup_interval(self, self_inner: Any) -> None:
        with self._lock:
            if hasattr(self, 'interval'):
                return

            if isinstance(self._calls_per_second, float):
                value = self._calls_per_second
            else:
                value = self._calls_per_second(self_inner)
            assert value > 0
            self.interval = 1.0 / value
