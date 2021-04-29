import pytest
from requests_cache import CacheMixin
from requests_toolbelt.adapters.fingerprint import FingerprintAdapter
from typing import cast

from reqcli.config import Configuration
from reqcli.type import TypeLoadConfig
from reqcli.source import SourceConfig, UnloadableType, ReqData
from reqcli.source.ratelimit import RateLimitedSession, RateLimitingMixin

from ..conftest import MOCK_PATH, BaseTypeTest, _get_source


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


@pytest.mark.parametrize('skip, expected_cache_status', [
    (True, (False, False, False)),
    (False, (False, True, True))
])
def test_skip_cache(skip, expected_cache_status):
    source = _get_source(None)
    reqdata = ReqData(path=MOCK_PATH)

    for expected in expected_cache_status:
        result = source.get(reqdata, skip_cache=skip)
        assert result.from_cache is expected  # type: ignore
        assert result.content == b'response'


# config stuff

def test_config__enable_cache():
    def get_session(cache):
        return _get_source(SourceConfig(enable_cache=cache))._session

    # caching disabled
    session = get_session(False)
    assert isinstance(session, RateLimitingMixin)
    assert not isinstance(session, CacheMixin)

    # caching enabled
    session = get_session(True)
    assert isinstance(session, RateLimitingMixin)
    assert isinstance(session, CacheMixin)


def test_config__cache_response_codes():
    source = _get_source(SourceConfig(enable_cache=True, cache_response_codes=[418]))
    assert list(cast(CacheMixin, source._session).allowable_codes) == [418]


def test_config__http_retries():
    source = _get_source(SourceConfig(http_retries=1337))
    for prefix in ('http://', 'https://'):
        assert source._session.adapters[prefix].max_retries.total == 1337


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
