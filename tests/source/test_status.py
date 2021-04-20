import re
import pytest
import requests

from reqcli.source import StatusCheckMode, SourceConfig, ReqData
from reqcli.errors import ResponseStatusError

from ..conftest import MOCK_BASE, MOCK_URL, _get_source


@pytest.fixture(autouse=True)
def mock_status(requests_mock):
    def status_callback(request, context):
        context.status_code = int(request.url.split('/')[-1])
        return f'code: {context.status_code}'
    requests_mock.get(re.compile(MOCK_BASE + r'code/\d+$'), text=status_callback)


@pytest.mark.parametrize('mode, success, fail', [
    (StatusCheckMode.NONE, [200, 300, 400, 500], []),
    (StatusCheckMode.CHECK_ERROR, [200, 300], [400, 500]),
    (StatusCheckMode.REQUIRE_200, [200], [204, 300, 400, 500])
])
@pytest.mark.parametrize('func_name', ('get', 'get_reader'))
def test_status(mode, success, fail, func_name):
    source = _get_source(SourceConfig(response_status_checking=mode))
    func = getattr(source, func_name)

    def check(code):
        result = func(ReqData(path=f'code/{code}'))
        if hasattr(result, '__enter__'):
            with result:
                pass

    for code in success:
        check(code)
    for code in fail:
        with pytest.raises(ResponseStatusError):
            check(code)


def test_status_invalid():
    with pytest.raises(AssertionError):
        StatusCheckMode.check(object(), requests.get(MOCK_URL))  # type: ignore
