import os
import contextlib
import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests_toolbelt.adapters.fingerprint import FingerprintAdapter
from typing import Iterator, TypeVar, Union, Optional, overload

from . import cachemanager, ratelimit
from .config import SourceConfig
from .reqdata import ReqData
from .unloadable import UnloadableType

from .. import reader, utils
from ..config import Configuration
from ..errors import ResponseStatusError
from ..type import BaseTypeLoadable


_TBaseTypeLoadable = TypeVar('_TBaseTypeLoadable', bound=BaseTypeLoadable)


class BaseSource:
    def __init__(self, base_reqdata: ReqData, config: Optional[SourceConfig], *, verify_tls: bool = True, require_fingerprint: Optional[str] = None):
        # build base request data
        self._base_reqdata = ReqData(
            path='',
            headers={'User-Agent': Configuration.default_user_agent}
        )
        self._base_reqdata += base_reqdata

        # use supplied config or default
        self._config = config if config is not None else SourceConfig()

        self._session = requests.Session()
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
    def _create_type(self, reqdata: ReqData, loadable: _TBaseTypeLoadable, *, skip_store_to_cache: bool = False) -> _TBaseTypeLoadable:
        ...

    @overload
    def _create_type(self, reqdata: ReqData, *, skip_store_to_cache: bool = False) -> UnloadableType:
        ...

    def _create_type(self, reqdata: ReqData, loadable: Optional[_TBaseTypeLoadable] = None, *, skip_store_to_cache: bool = False) -> Union[_TBaseTypeLoadable, UnloadableType]:
        if loadable is not None:
            # first overload
            with self.get_reader(reqdata, skip_store_to_cache=skip_store_to_cache) as reader:
                return loadable.load(reader, self._config.type_load_config)
        else:
            # second overload
            return UnloadableType(self, reqdata, skip_store_to_cache)

    def get_nocache(self, reqdata: ReqData) -> requests.Response:
        res = self.__get_nocache_internal(reqdata)
        self.__check_status(res)
        return res

    @contextlib.contextmanager
    def get_reader(self, reqdata: ReqData, *, skip_store_to_cache: bool = False) -> Iterator[reader.Reader]:
        with self.__get_reader_internal(reqdata, skip_store_to_cache) as reader:
            if reader.metadata:  # if this is None, request was loaded from cache and successful
                self.__check_status(reader.metadata)
            yield reader

    @ratelimit.limit(lambda self: self._config.requests_per_second)
    def __get_nocache_internal(self, reqdata: ReqData, already_merged: bool = False) -> requests.Response:
        # optimization to avoid having to merge twice
        if not already_merged:
            reqdata = self._base_reqdata + reqdata

        res = self._session.get(
            url=reqdata.path,
            headers=reqdata.headers,
            params=reqdata.params,
            cert=reqdata.cert,
            stream=True,
            allow_redirects=False
        )
        return res

    @contextlib.contextmanager
    def __get_reader_internal(self, reqdata: ReqData, skip_store_to_cache: bool) -> Iterator[reader.Reader]:
        merged_reqdata = self._base_reqdata + reqdata
        cache_path = cachemanager.get_path(merged_reqdata)
        meta_path = cachemanager.get_metadata_path(cache_path)

        # try loading from cache if configured and file exists
        if self._config.load_from_cache and os.path.isfile(cache_path):
            metadata = None
            if os.path.isfile(meta_path):
                metadata = reader.Metadata.from_file(meta_path)

            with open(cache_path, 'rb') as fc:
                yield reader.IOReader(fc, metadata)
        else:
            with self.__get_nocache_internal(merged_reqdata, True) as res:
                metadata = reader.Metadata.from_response(res)
                res_reader = reader.ResponseReader(res, metadata)

                # cache data if configured, return basic reader otherwise
                if (not skip_store_to_cache) and self._config.store_to_cache:
                    # additionally store metadata to separate file
                    if self._config.store_metadata:
                        utils.misc.create_dirs_for_file(meta_path)
                        metadata.write_file(meta_path)

                    # avoid creating a cache file if the request failed and metadata wasn't stored.
                    # if the file were to be kept regardless of errors, it would later be impossible
                    # to distinguish successful and failed requests, as metadata wasn't written

                    with reader.CachingReader(res_reader, cache_path, [ResponseStatusError] if self._config.store_failed_requests else []) as caching_reader:
                        yield caching_reader
                else:
                    yield res_reader

    def __check_status(self, obj: Union[requests.Response, reader.Metadata]) -> None:
        self._config.response_status_checking.check(obj)
