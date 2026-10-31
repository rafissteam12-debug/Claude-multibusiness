"""Small helpers for crafting XML in tests (not a test module)."""
from lxml import etree

NS = {"rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
      "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
      "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"}


def tree(xml: bytes):
    return etree.fromstring(xml)


def remove(root, xpath):
    nodes = root.xpath(xpath, namespaces=NS)
    assert nodes, xpath
    for n in nodes:
        n.getparent().remove(n)
    return root


def set_text(root, xpath, text):
    nodes = root.xpath(xpath, namespaces=NS)
    assert nodes, xpath
    for n in nodes:
        n.text = text
    return root


def dump(root) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


def ids(report, layer=None):
    return {e["id"] for l in report["layers"] if layer in (None, l["name"]) for e in l["errors"]}
