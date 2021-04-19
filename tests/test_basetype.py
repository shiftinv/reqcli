import io
from typing import Optional
import pytest
from dataclasses import dataclass
from construct import Byte, Struct, Computed

from reqcli.type import BaseTypeLoadable, BaseTypeLoadableConstruct, XmlBaseType, TypeLoadConfig
from reqcli.errors import TypeAlreadyLoadedError, XmlSchemaError
from reqcli.utils import xml


@pytest.fixture()
def testtype():
    class TestType(BaseTypeLoadable):
        def _read(self, reader, config):
            self.test_data = reader.read()
            self.test_config = config
    return TestType()


def test_basetype__load__twice(testtype):
    testtype.load_bytes(b'')
    with pytest.raises(TypeAlreadyLoadedError):
        testtype.load_bytes(b'')


def test_basetype__load__config(testtype):
    config = TypeLoadConfig()
    testtype.load_bytes(b'', config)
    assert testtype.test_config is config


def test_basetype__load_file(testtype, tmp_path):
    filename = str(tmp_path / 'testfile')
    with open(filename, 'wb') as f:
        f.write(b'testdata')

    testtype.load_file(filename)

    assert testtype.test_data == b'testdata'


def test_basetype__load_bytes(testtype):
    testtype.load_bytes(b'testdata')
    assert testtype.test_data == b'testdata'


def test_basetypeconstruct():
    # create types/structs
    class TestTypeConstruct(BaseTypeLoadableConstruct):
        def _read(self, reader, config):
            self.test_construct = self._parse_construct(reader.read(), config)

    struct = Struct(
        'a' / Byte,
        'b' / Byte,
        'param' / Computed(lambda ctx: ctx._params.testparam)
    )

    config = TypeLoadConfig(construct_kwargs={'testparam': 42})

    # load
    testtype = TestTypeConstruct(struct)
    testtype.load_bytes(b'\x01\x02', config)

    assert testtype.test_construct == {'a': 1, 'b': 2, 'param': 42}


@pytest.mark.parametrize('schema, xml_str, expect_err', [
    # valid schema, no superset
    (({'value': None}, False), '<value>test</value>', False),
    # superset schema
    (({'value': None, 'other': None}, True), '<value>test</value>', False),
    # no schema
    (None, '<value>test</value>', False),
    # invalid xml
    (({'value': None}, False), '<y>z</y>', True)
])
def test_xmlbasetype(schema, xml_str, expect_err):

    @dataclass
    class XmlType(XmlBaseType):
        x: Optional[str] = None

        @classmethod
        def _parse_internal(cls, xml):
            return {'x': xml.value.text}

        if schema:
            @classmethod
            def _get_schema(cls):
                return schema

    xmldata = xml.read_object(io.BytesIO(f'<root>{xml_str}</root>'.encode()))

    if expect_err:
        with pytest.raises(XmlSchemaError):
            XmlType._parse(xmldata)
    else:
        xmltype = XmlType._parse(xmldata)
        assert xmltype.x == 'test'
