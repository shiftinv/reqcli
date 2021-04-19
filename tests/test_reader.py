import os
import io
import pytest
import requests

from reqcli.reader import Reader, IOReader, ResponseReader
from reqcli.errors import ReaderError


@pytest.fixture()
def reader():
    data = b'testdata'
    return Reader(io.BytesIO(data), len(data))


def test_reader__read_tell(reader: Reader) -> None:
    assert reader.tell() == 0
    assert reader.read(2) == b'te'
    assert reader.read() == b'stdata'
    assert reader.tell() == reader.size


def test_reader__seek(reader: Reader) -> None:
    reader.read(4)
    reader.seek(2, os.SEEK_SET)
    assert reader.read() == b'stdata'


def test_ioreader_size():
    assert IOReader(io.BytesIO(b'x' * 42)).size == 42


def test_responsereader_stream(requests_mock):
    requests_mock.get('http://test')
    with pytest.raises(ReaderError):
        ResponseReader(requests.get('http://test'))


@pytest.mark.parametrize('headers, size', [
    ({}, None),
    ({'content-length': '42'}, 42),
    ({'content-length': '42', 'content-encoding': 'gzip'}, None),
])
def test_responsereader_size(requests_mock, headers, size):
    requests_mock.get('http://test', headers=headers)
    assert ResponseReader(requests.get('http://test', stream=True)).size == size
