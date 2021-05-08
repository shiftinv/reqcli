import pytest
from typing import Any, Optional

from reqcli.config import Configuration
from reqcli.type import BaseTypeLoadable
from reqcli.source import BaseSource, ReqData, SourceConfig


@pytest.fixture(autouse=True)
def config_setup(request):
    Configuration.cache_backend = 'memory'

    if 'no_ratelimit_patch' not in request.keywords:
        # disable ratelimit while testing (unless set explicitly)
        orig_init = SourceConfig.__init__

        def patched_init(self, *args, **kwargs):
            orig_init(self, *args, **kwargs)
            if self.requests_per_second == SourceConfig.requests_per_second:
                object.__setattr__(self, 'requests_per_second', 1000000)

        SourceConfig.__init__ = patched_init  # type: ignore


def pytest_configure(config):
    config.addinivalue_line(
        'markers', 'no_ratelimit_patch: don\'t disable ratelimit while testing'
    )


MOCK_BASE = 'http://test/'
MOCK_BASE2 = 'http://test2/'
MOCK_PATH = 'testpath'
MOCK_URL = MOCK_BASE + MOCK_PATH
MOCK_URL2 = MOCK_BASE2 + MOCK_PATH


@pytest.fixture(autouse=True)
def mock_base(requests_mock):
    requests_mock.get(MOCK_URL, text='response')
    requests_mock.get(MOCK_URL2, text='response')


class BaseTypeTest(BaseTypeLoadable):
    def _read(self, reader, config):
        self.test_data = reader.read()
        self.test_config = config


class BaseSourceTest(BaseSource):
    def get_test(self, **kwargs):
        return self._create_type(
            ReqData(path=MOCK_PATH),
            BaseTypeTest(),
            **kwargs
        )


def _get_source(config: Optional[SourceConfig], base: Optional[str] = None, **kwargs: Any) -> BaseSourceTest:
    return BaseSourceTest(ReqData(path=base or MOCK_BASE), config, **kwargs)
