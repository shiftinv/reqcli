import io
import lxml.objectify
from xml.etree import ElementTree as ET
from typing import Any, Tuple, Set, Dict, Optional, Iterator

from . import dicts
from .. import reader


SchemaType = Dict[str, Any]  # needs `Any` type since there's no support for self-recursive types (yet)


def read(data: bytes) -> ET.ElementTree:
    return ET.parse(io.BytesIO(data))


def read_object(data: bytes) -> lxml.objectify.ObjectifiedElement:
    return lxml.objectify.parse(io.BytesIO(data)).getroot()


def load_from_reader(reader: 'reader.Reader', root_tag: Optional[str] = None) -> lxml.objectify.ObjectifiedElement:
    data = reader.read()
    tree = read_object(data)
    children = tree.getchildren()
    assert len(children) == 1
    if root_tag:
        assert children[0].tag == root_tag
    return children[0]


def get_text(xml: lxml.objectify.ObjectifiedElement, attr: str) -> Optional[str]:
    val = getattr(xml, attr, None)
    return val.text if val is not None else None


def iter_children(xml: lxml.objectify.ObjectifiedElement) -> Iterator[Tuple[lxml.objectify.ObjectifiedElement, str, str]]:
    for child in xml.getchildren():
        yield (child, child.tag, child.text)


def get_tag_schema(xml: lxml.objectify.ObjectifiedElement) -> Optional[SchemaType]:
    children = xml.getchildren()
    if not children:
        return None

    d = {}
    for c in children:
        d[c.tag] = get_tag_schema(c)
    return d


def validate_schema(xml: lxml.objectify.ObjectifiedElement, target_hierarchy: Optional[SchemaType], superset: bool) -> None:
    h = get_tag_schema(xml)
    if (not superset and target_hierarchy != h) or (superset and not dicts.is_dict_subset_deep(h, target_hierarchy)):
        raise RuntimeError(f'unexpected XML structure\nexpected{" subset of" if superset else ""}:\n\t{target_hierarchy}\ngot:\n\t{h}')


def get_child_tags(xml: lxml.objectify.ObjectifiedElement) -> Set[str]:
    return {el.tag for el in xml.getchildren()}
