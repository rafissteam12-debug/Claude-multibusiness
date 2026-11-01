"""Free checker helpers: size/type limits before parsing, safe format detection, German summary."""
from __future__ import annotations

import re

from lxml import etree

CII_NS = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
UBL_NS = ("urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
          "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2")
_DTD = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.I)


def kind_of(data: bytes, filename: str) -> str | None:
    """'xml', 'pdf' or None (unsupported)."""
    head = data[:1024].lstrip(b"\xef\xbb\xbf \t\r\n")
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"<"):
        return "xml"
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return "pdf"
    if name.endswith(".xml"):
        return "xml"
    return None


def safe_parser() -> etree.XMLParser:
    return etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False, load_dtd=False,
                           dtd_validation=False, remove_comments=True)


def detect_format(data: bytes, kind: str) -> str:
    """XRechnung-CII | XRechnung-UBL | ZUGFeRD | unknown. Never resolves entities; DOCTYPE -> unknown."""
    if kind == "pdf":
        return "ZUGFeRD"
    if _DTD.search(data[:65536]):
        return "unknown"
    try:
        root = etree.fromstring(data, safe_parser())
    except etree.XMLSyntaxError:
        return "unknown"
    ns = etree.QName(root).namespace
    if ns == CII_NS:
        return "XRechnung-CII"
    if ns in UBL_NS:
        return "XRechnung-UBL"
    return "unknown"


def summary_de(report: dict, fmt: str) -> str:
    skipped = [f"{l['name']} ({l['skipped_reason']})" for l in report.get("layers", []) if not l.get("ran")]
    n_err = sum(len(l.get("errors", [])) for l in report.get("layers", []))
    if report.get("valid"):
        text = "Gültig: Die Datei hat alle ausgeführten Pflichtprüfungen ohne Fehler bestanden."
    elif fmt == "unknown" and n_err == 0:
        text = "Nicht geprüft: Das Format wurde nicht erkannt."
    else:
        text = f"Nicht gültig: {n_err} Fehler gefunden." if n_err else "Nicht gültig: Pflichtprüfungen konnten nicht ausgeführt werden."
    if skipped:
        text += " Übersprungen (nicht bestanden, sondern nicht geprüft): " + "; ".join(skipped) + "."
    if report.get("totals_warning"):
        text += " Hinweis: Die Summen weichen von den Quelldaten ab."
    return text
