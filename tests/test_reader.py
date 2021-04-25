import os
import io
import gzip
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


def test_reader_funcs():
    class TestReader(Reader):
        # existing method
        def seek(self, o, w):
            pass

    stream = io.BytesIO()
    reader = TestReader(stream, 0)
    assert reader.read == stream.read
    assert reader.readable == stream.readable
    assert reader.seek.__func__ == TestReader.seek  # type: ignore


def test_reader_funcs_new():
    class TestReader(Reader):
        # new method
        def read(self, n):
            pass

    stream = io.BytesIO()
    reader = TestReader(stream, 0)
    assert reader.readable == stream.readable
    assert reader.read.__func__ == TestReader.read  # type: ignore


def test_ioreader_size():
    assert IOReader(io.BytesIO(b'x' * 42)).size == 42


def test_responsereader__stream(requests_mock):
    requests_mock.get('http://test')
    with pytest.raises(ReaderError):
        ResponseReader(requests.get('http://test'))


@pytest.mark.parametrize('headers, size', [
    ({}, None),
    ({'content-length': '42'}, 42),
    ({'content-length': '42', 'content-encoding': 'gzip'}, None),
])
def test_responsereader__size(requests_mock, headers, size):
    requests_mock.get('http://test', headers=headers)
    assert ResponseReader(requests.get('http://test', stream=True)).size == size


def test_responsereader__tell(requests_mock):
    requests_mock.get('http://test', content=b'response')
    reader = ResponseReader(requests.get('http://test', stream=True))
    assert reader.tell() == 0
    reader.read(5)
    assert reader.tell() == 5


def test_responsereader__tell_encoded(requests_mock):
    requests_mock.get(
        'http://test',
        content=gzip.compress(b'response' + os.urandom(500)),
        headers={'Content-Encoding': 'gzip'}
    )
    reader = ResponseReader(requests.get('http://test', stream=True))
    assert reader.tell() == 0
    read_data = reader.read(100)  # read_data is not necessarily 100 bytes
    assert read_data.startswith(b'response')
    assert reader.tell() == len(read_data)
