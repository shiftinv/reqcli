import io
import pytest

from reqcli.utils import dicts, xml
from reqcli.errors import XmlLoadError, XmlSchemaError


# dicts.py

@pytest.mark.parametrize('other', [None, {}, {1: 2, 3: {}}])
def test_dicts__is_dict_subset_deep__none(other):
    assert dicts.is_dict_subset_deep(None, other)
    if other is not None:
        assert not dicts.is_dict_subset_deep(other, None)


@pytest.mark.parametrize('a, b', [
    ({}, {0: 1}),
    ({0: 1}, {0: 1}),
    ({0: 1}, {0: 1, 2: 3}),
    ({0: 1}, {0: 1, 'x': {2: 3}}),
    ({0: {}}, {0: {}, 1: 2}),
    ({'x': {0: 1}}, {'x': {0: 1, 2: 3}, 'y': {5: 6}})
])
def test_dicts__is_dict_subset_deep__valid(a, b):
    assert dicts.is_dict_subset_deep(a, b)


@pytest.mark.parametrize('a, b', [
    ({0: 0}, {0: 1}),
    ({0: 1}, {}),
    ({0: 1, 'x': {}}, {0: 1}),
    ({0: 1, 'x': {}}, {0: 1, 'x': []}),
    ({'x': {0: 1}}, {'x': {}})
])
def test_dicts__is_dict_subset_deep__invalid(a, b):
    assert not dicts.is_dict_subset_deep(a, b)


# xml.py

def test_xml__load_root():
    # invalid
    with pytest.raises(XmlLoadError):
        xml.load_root(io.BytesIO(b'<root><child1/><child2/></root>'))
    with pytest.raises(XmlLoadError):
        xml.load_root(io.BytesIO(b'<root><child/></root>'), 'x')

    # valid
    for name in (None, 'child'):
        node = xml.load_root(io.BytesIO(b'<root><child><el>test</el></child></root>'), name)
        assert node.tag == 'child'
        assert node.el.text == 'test'


@pytest.fixture()
def xml_element():
    data = b'''<?xml version="1.0" encoding="UTF-8"?>
        <root>
            <node>
                <el1>text1.0</el1>
                <el1>text1.1</el1>
                <el2 attr="val">text2</el2>
            </node>
        </root>
    '''
    return xml.read_object(io.BytesIO(data))


def test_xml__get_text(xml_element):
    assert xml.get_text(xml_element.node, 'el2') == 'text2'
    assert xml.get_text(xml_element.node, 'doesnotexist') is None


def test_xml__iter_children(xml_element):
    it = xml.iter_children(xml_element.node)
    assert next(it) == (xml_element.node.el1[0], 'el1', 'text1.0')
    assert next(it) == (xml_element.node.el1[1], 'el1', 'text1.1')
    assert next(it) == (xml_element.node.el2, 'el2', 'text2')
    assert next(it, None) is None


def test_xml__get_tag_schema(xml_element):
    assert xml.get_tag_schema(xml_element) == {'node': {'el1': None, 'el2': None}}


def test_xml__validate_schema(xml_element):
    xml.validate_schema(xml_element, {'node': {'el1': None, 'el2': None}}, False)
    with pytest.raises(XmlSchemaError):
        xml.validate_schema(xml_element, {'node': {'el1': None}}, False)
    with pytest.raises(XmlSchemaError):
        xml.validate_schema(xml_element, {'node': {'el1': None, 'el2': None, 'el3': None}}, False)


def test_xml__validate_schema__superset(xml_element):
    xml.validate_schema(xml_element, {'node': {'el1': None, 'el2': None, 'el3': None}}, True)
    with pytest.raises(XmlSchemaError):
        xml.validate_schema(xml_element, {'node': {'el1': None}}, True)


def test_xml__get_child_tags(xml_element):
    assert xml.get_child_tags(xml_element) == {'node'}
    assert xml.get_child_tags(xml_element.node) == {'el1', 'el2'}
