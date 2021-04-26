import urllib3
import logging
import requests
import contextlib
from requests.adapters import HTTPAdapter
from requests_toolbelt.adapters.fingerprint import FingerprintAdapter
from typing import Iterator, TypeVar, Union, Optional, overload

from .config import SourceConfig
from .reqdata import ReqData
from .unloadable import UnloadableType
from .ratelimit import RateLimitedSession, CachedRateLimitedSession

from .. import reader
from ..config import Configuration
from ..type import BaseTypeLoadable


_TBaseTypeLoadable = TypeVar('_TBaseTypeLoadable', bound=BaseTypeLoadable)

_cache_disabled_hook = 'get_cache_disabled'

_logger = logging.getLogger(__name__)


class BaseSource:
    def __init__(self, base_reqdata: ReqData, config: Optional[SourceConfig], *, verify_tls: bool = True, require_fingerprint: Optional[str] = None):
        # use supplied config or default
        if config is None:
            self._config = SourceConfig()
            config_str = 'default config'
        else:
            self._config = config
            config_str = f'config {config}'

        _logger.debug(f'Initializing source {type(self).__name__} with reqdata {base_reqdata} and {config_str}')

        # build base request data
        self._base_reqdata = ReqData(
            path='',
            headers={'User-Agent': Configuration.default_user_agent}
        )
        self._base_reqdata += base_reqdata

        self._session: Union[requests.Session, CachedRateLimitedSession]
        if self._config.enable_cache:
            # this is a hack for disabling the cache for specific requests; adding custom data to `PreparedRequest`
            #  objects through .get/.request is surprisingly difficult (unless I'm missing something very obvious).
            # this could probably be solved with more subclassing and overriding methods, but it would likely be more complex

            # add new key to list of hooks
            if _cache_disabled_hook not in requests.hooks.HOOKS:
                requests.hooks.HOOKS.append(_cache_disabled_hook)

            # returns false if request should not be cached
            def filter_fn(r: Union[requests.PreparedRequest, requests.Response]) -> bool:
                if isinstance(r, requests.PreparedRequest):
                    return not requests.hooks.dispatch_hook(_cache_disabled_hook, r.hooks, r)
                return True

            # create cached session
            self._session = CachedRateLimitedSession(
                cache_name=Configuration.cache_name,
                backend=Configuration.cache_backend,
                allowable_codes=set(self._config.cache_response_codes),
                filter_fn=filter_fn,
                include_get_headers=True,
                fast_save=True,
                requests_per_second=self._config.requests_per_second
            )
        else:
            # create non-cached session
            self._session = RateLimitedSession(
                requests_per_second=self._config.requests_per_second
            )

        self._session.verify = verify_tls

        # set up retries
        retry = urllib3.util.retry.Retry(
            total=self._config.http_retries,
            backoff_factor=0.5,
            redirect=False,
            raise_on_redirect=False,
            status_forcelist={420, 429, *range(500, 520)},
            raise_on_status=False
        )
        self._session.mount('http://', HTTPAdapter(max_retries=retry))

        if require_fingerprint is not None:
            # FingerprintAdapter passes kwargs to underlying HTTPAdapter
            self._session.mount('https://', FingerprintAdapter(require_fingerprint, max_retries=retry))
            _logger.debug(f'Using server fingerprint {require_fingerprint!r} for HTTPS connections')
        else:
            self._session.mount('https://', HTTPAdapter(max_retries=retry))

    @overload
    def _create_type(self, reqdata: ReqData, loadable: _TBaseTypeLoadable, *, skip_cache: bool = False) -> _TBaseTypeLoadable:
        ...

    @overload
    def _create_type(self, reqdata: ReqData, *, skip_cache: bool = False) -> UnloadableType:
        ...

    def _create_type(self, reqdata: ReqData, loadable: Optional[_TBaseTypeLoadable] = None, *, skip_cache: bool = False) -> Union[_TBaseTypeLoadable, UnloadableType]:
        if loadable is not None:
            # first overload
            with self.get_reader(reqdata, skip_cache=skip_cache) as reader:
                return loadable.load(reader, self._config.type_load_config)
        else:
            # second overload
            return UnloadableType(self, reqdata, skip_cache)

    def get(self, reqdata: ReqData, *, skip_cache: bool = False) -> requests.Response:
        res = self.__get_internal(reqdata, skip_cache)
        self.__check_status(res)
        return res

    @contextlib.contextmanager
    def get_reader(self, reqdata: ReqData, *, skip_cache: bool = False) -> Iterator[reader.Reader]:
        with self.get(reqdata, skip_cache=skip_cache) as res:
            yield reader.ResponseReader(res)

    def __get_internal(self, reqdata: ReqData, skip_cache: bool) -> requests.Response:
        reqdata = self._base_reqdata + reqdata

        _logger.debug(f'Sending request {reqdata}' + (' [cache disabled]' if skip_cache else ''))

        res = self._session.get(
            url=reqdata.path,
            headers=reqdata.headers,
            params=reqdata.params,
            cert=reqdata.cert,
            stream=True,
            allow_redirects=False,
            # used by `filter_fn` for bypassing the cache (see `__init__` above)
            hooks={_cache_disabled_hook: lambda r: skip_cache}
        )

        if getattr(res, 'from_cache', False):
            _logger.debug(f'Got cached response for request to {reqdata.path}')

        return res

    def __check_status(self, obj: requests.Response) -> None:
        self._config.response_status_checking.check(obj)
