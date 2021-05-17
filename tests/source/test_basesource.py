import pytest
import requests
from unittest.mock import patch
from requests_cache import CacheMixin
from requests_toolbelt.adapters.fingerprint import FingerprintAdapter
from typing import cast

from reqcli.config import Configuration
from reqcli.type import TypeLoadConfig
from reqcli.source import SourceConfig, UnloadableType, ReqData, StatusCheckMode
from reqcli.source.ratelimit import RateLimitedSession, RateLimitingMixin

from ..conftest import MOCK_BASE, MOCK_PATH, BaseTypeTest, _get_source


def test_fingerprint():
    source = _get_source(SourceConfig(http_retries=1337), require_fingerprint='12:34:ab:cd')
    adapter = source._session.adapters['https://']
    # check adapter
    assert isinstance(adapter, FingerprintAdapter)
    # ensure retries are still enabled
    assert adapter.max_retries.total == 1337


@pytest.mark.parametrize('verify_tls', (True, False))
def test_verify(verify_tls):
    assert _get_source(None, verify_tls=verify_tls)._session.verify is verify_tls


@pytest.mark.parametrize('skip_cache', (True, False))
def test_unloadable(skip_cache):
    source = _get_source(None)
    reqdata = ReqData(path=MOCK_PATH)

    inst = source._create_type(reqdata, skip_cache=skip_cache)

    assert isinstance(inst, UnloadableType)
    assert inst.reqdata is reqdata
    assert inst.kwargs['skip_cache'] is skip_cache
    with inst.get_reader() as reader:
        assert reader.read() == b'response'


def test_get():
    result = _get_source(None).get_test()
    assert isinstance(result, BaseTypeTest)
    assert result.test_data == b'response'


@pytest.mark.parametrize('force, expected_type', [
    (False, BaseTypeTest),
    (True, UnloadableType)
])
def test_force_unloadable(force, expected_type):
    source = _get_source(None)
    assert type(source.get_test(force_unloadable=force)) is expected_type


@pytest.mark.parametrize('skip, expected_cache_status', [
    (True, (False, False, False)),
    (False, (False, True, True))
])
@pytest.mark.parametrize('callable', (True, False))
def test_skip_cache(skip, expected_cache_status, callable):
    source = _get_source(None)
    reqdata = ReqData(path=MOCK_PATH)

    if callable:
        skip_val = skip
        def skip(r):  # noqa
            assert isinstance(r, requests.PreparedRequest)
            return skip_val

    for expected in expected_cache_status:
        result = source.get(reqdata, skip_cache=skip)
        assert result.from_cache is expected  # type: ignore
        assert result.content == b'response'


@pytest.mark.parametrize('skip', (True, False))
def test_skip_cache_read(skip, requests_mock):
    path = 'test_skip_cache_read'
    url = MOCK_BASE + path
    requests_mock.get(url, [{'text': 'first'}, {'text': 'second'}])

    source = _get_source(None)
    session = cast(CacheMixin, source._session)
    reqdata = ReqData(path=path)

    res = source.get(reqdata, skip_cache_read=skip)
    # response should have been stored in cache either way
    assert url in session.cache.urls
    # first response is never from cache
    assert res.from_cache is False  # type: ignore
    assert res.text == 'first'

    res = source.get(reqdata, skip_cache_read=skip)
    # second response should only be from cache if skip_cache_read=False
    assert res.from_cache is (not skip)  # type: ignore
    # if skip_cache_read=True, new request should have been sent (and stored)
    expected_text = 'second' if skip else 'first'
    assert res.text == expected_text

    # new request with skip_cache_read=False should return same data as previous one
    res = source.get(reqdata, skip_cache_read=False)
    assert res.from_cache is True  # type: ignore
    assert res.text == expected_text


@pytest.mark.parametrize('skip', (True, False))
def test_skip_cache_write(skip, requests_mock):
    path = 'test_skip_cache_write'
    url = MOCK_BASE + path
    requests_mock.get(url, [{'text': 'first'}, {'text': 'second'}, {'text': 'third'}])

    source = _get_source(None)
    session = cast(CacheMixin, source._session)
    reqdata = ReqData(path=path)

    res = source.get(reqdata, skip_cache_write=True)
    # response should not be in cache
    assert url not in session.cache.urls
    assert res.text == 'first'

    res = source.get(reqdata, skip_cache_write=skip)
    # second response should be in cache only if skip_cache_write=False
    assert (url in session.cache.urls) is not skip
    assert res.from_cache is False  # type: ignore
    assert res.text == 'second'

    res = source.get(reqdata, skip_cache_write=False)
    # response should be in cache
    assert url in session.cache.urls
    assert res.from_cache is not skip  # type: ignore
    # if second response was not written to cache, we should've gotten the third one now
    expected_text = 'third' if skip else 'second'
    assert res.text == expected_text


# config stuff

def test_config__enable_cache():
    def get(cache):
        source = _get_source(SourceConfig(enable_cache=cache))
        return source, source._session

    # caching disabled
    source, session = get(False)
    assert isinstance(session, RateLimitingMixin)
    assert not isinstance(session, CacheMixin)
    source.get_test()

    # caching enabled
    source, session = get(True)
    assert isinstance(session, RateLimitingMixin)
    assert isinstance(session, CacheMixin)
    source.get_test()


def test_config__cache_response_codes():
    source = _get_source(SourceConfig(enable_cache=True, cache_response_codes=[418]))
    assert list(cast(CacheMixin, source._session).allowable_codes) == [418]


def test_config__http_retries():
    source = _get_source(SourceConfig(http_retries=1337))
    for prefix in ('http://', 'https://'):
        assert source._session.adapters[prefix].max_retries.total == 1337


def test_config__timeout():
    source = _get_source(SourceConfig(timeout=42, response_status_checking=StatusCheckMode.NONE))
    with patch.object(source._session, 'get') as mock_get:
        source.get(ReqData(path=MOCK_PATH))
        assert mock_get.call_args[1]['timeout'] == 42


@pytest.mark.parametrize('cached', (True, False))
def test_config__requests_per_second(cached):
    source = _get_source(SourceConfig(enable_cache=cached, requests_per_second=64))
    assert cast(RateLimitedSession, source._session)._ratelimit_interval == 1.0 / 64


def test_config__type_load_config():
    type_load_config = TypeLoadConfig()
    source = _get_source(SourceConfig(type_load_config=type_load_config))
    assert source.get_test().test_config is type_load_config


def test_config__type_load_config__global_default():

    class TestConfig(TypeLoadConfig):
        pass

    Configuration.type_load_config_type = TestConfig
    source = _get_source(SourceConfig())
    assert isinstance(source.get_test().test_config, TestConfig)
