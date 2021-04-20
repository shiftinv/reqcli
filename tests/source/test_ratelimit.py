import pytest
from unittest.mock import patch

from reqcli.source import SourceConfig, ReqData
from reqcli.source.ratelimit import RateLimitedSession, RateLimitingMixin

from ..conftest import MOCK_BASE2, MOCK_URL, _get_source


@pytest.fixture(autouse=True)
def reset_ratelimits():
    getattr(RateLimitingMixin, '_RateLimitingMixin__last_call').clear()


def new_source(*, base=None, cache=False):
    return _get_source(SourceConfig(enable_cache=cache, requests_per_second=0.1), base)


@pytest.mark.no_ratelimit_patch
@patch('time.sleep')
def test_wait(mock_sleep):
    new_source().get_test()

    new_source().get_test()
    assert mock_sleep.call_count == 1
    assert 9 <= mock_sleep.call_args[0][0] <= 10

    new_source().get_test()
    assert mock_sleep.call_count == 2
    assert 19 <= mock_sleep.call_args[0][0] <= 20


@pytest.mark.no_ratelimit_patch
@patch('time.sleep')
def test_different_hosts(mock_sleep):
    new_source().get_test()
    assert mock_sleep.call_count == 0

    new_source(base=MOCK_BASE2).get_test()
    assert mock_sleep.call_count == 0

    new_source(base=MOCK_BASE2).get_test()
    assert mock_sleep.call_count == 1


@pytest.mark.no_ratelimit_patch
@patch('time.sleep')
def test_cached_nolimit(mock_sleep):
    source = new_source(cache=True)
    reqdata = ReqData(path=MOCK_URL)

    assert not source.get(reqdata).from_cache
    assert mock_sleep.call_count == 0

    assert source.get(reqdata).from_cache
    assert mock_sleep.call_count == 0


@pytest.mark.parametrize('rps', (-1, 0))
def test_invalid_rps(rps):
    with pytest.raises(AssertionError):
        RateLimitedSession(rps)
