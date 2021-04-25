import urllib3
import logging
import requests
import contextlib
import requests_cache
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

_logger = logging.getLogger(__name__)


class BaseSource:
    # note: this class is not thread-safe

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
            self._session = CachedRateLimitedSession(
                cache_name=Configuration.cache_name,
                backend=Configuration.cache_backend,
                allowable_codes=set(self._config.cache_response_codes),
                include_get_headers=True,
                fast_save=True,
                requests_per_second=self._config.requests_per_second
            )
        else:
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

        if skip_cache and isinstance(self._session, requests_cache.CacheMixin):
            # not thread-safe
            disable_cache_ctx = self._session.cache_disabled()
            cache_disabled = True
        else:
            disable_cache_ctx = contextlib.nullcontext()
            cache_disabled = False

        _logger.debug(f'Sending request {reqdata}' + (' [cache disabled]' if cache_disabled else ''))

        with disable_cache_ctx:
            res = self._session.get(
                url=reqdata.path,
                headers=reqdata.headers,
                params=reqdata.params,
                cert=reqdata.cert,
                stream=True,
                allow_redirects=False
            )

        if getattr(res, 'from_cache', False):
            _logger.debug(f'Got cached response for request to {reqdata.path}')

        return res

    def __check_status(self, obj: requests.Response) -> None:
        self._config.response_status_checking.check(obj)
