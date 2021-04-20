import urllib3
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


class BaseSource:
    # note: this class is not thread-safe

    def __init__(self, base_reqdata: ReqData, config: Optional[SourceConfig], *, verify_tls: bool = True, require_fingerprint: Optional[str] = None):
        # build base request data
        self._base_reqdata = ReqData(
            path='',
            headers={'User-Agent': Configuration.default_user_agent}
        )
        self._base_reqdata += base_reqdata

        # use supplied config or default
        self._config = config if config is not None else SourceConfig()

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
        else:
            disable_cache_ctx = contextlib.nullcontext()

        with disable_cache_ctx:
            res = self._session.get(
                url=reqdata.path,
                headers=reqdata.headers,
                params=reqdata.params,
                cert=reqdata.cert,
                stream=True,
                allow_redirects=False
            )

        return res

    def __check_status(self, obj: requests.Response) -> None:
        self._config.response_status_checking.check(obj)
