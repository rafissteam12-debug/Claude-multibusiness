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


def _guideline_from_xml(root) -> str:
    """CII: GuidelineSpecifiedDocumentContextParameter/ID; UBL: CustomizationID. Empty if absent."""
    ids = root.xpath("/*/*[local-name()='ExchangedDocumentContext']/*[local-name()='GuidelineSpecifiedDocumentContextParameter']"
                     "/*[local-name()='ID']/text() | /*/*[local-name()='CustomizationID']/text()")
    return (ids[0] if ids else "").strip()


def is_xrechnung_guideline(gid: str) -> bool:
    g = (gid or "").lower()
    return "xeinkauf.de:kosit:xrechnung" in g or "xeinkauf.de:kosit:extension:xrechnung" in g


def detect_format(data: bytes, kind: str, report: dict | None = None) -> str:
    """XRechnung-CII | XRechnung-UBL | ZUGFeRD | unknown, derived from the profile/guideline ID.

    XRechnung only for an XRechnung guideline ID; other recognised CII profiles (and PDFs) are ZUGFeRD/Factur-X;
    an unknown profile is 'unknown'. Never resolves entities; DOCTYPE -> unknown.
    """
    report = report or {}
    profile = report.get("profile")
    if profile == "unknown":
        return "unknown"
    gid = report.get("guideline_id") or ""
    if kind == "pdf":
        return "ZUGFeRD" if (profile or gid) else "unknown"
    if _DTD.search(data[:65536]):
        return "unknown"
    try:
        root = etree.fromstring(data, safe_parser())
    except etree.XMLSyntaxError:
        return "unknown"
    gid = gid or _guideline_from_xml(root)
    if not gid:
        return "unknown"
    ns = etree.QName(root).namespace
    if ns == CII_NS:
        return "XRechnung-CII" if is_xrechnung_guideline(gid) else "ZUGFeRD"
    if ns in UBL_NS:
        return "XRechnung-UBL" if is_xrechnung_guideline(gid) else "unknown"
    return "unknown"


UNKNOWN_PROFILE_DE = "Das Profil der Datei ist unbekannt oder wird nicht unterstützt."


def enforce_known_profile(report: dict, fmt: str) -> dict:
    """Rule 8 safety net: a file with an unknown profile/format is never reported as valid."""
    if report.get("valid") and (fmt == "unknown" or report.get("profile") == "unknown"):
        report["valid"] = False
        report["invalid_reason_de"] = UNKNOWN_PROFILE_DE
    return report


def summary_de(report: dict, fmt: str) -> str:
    skipped = [f"{l['name']} ({l['skipped_reason']})" for l in report.get("layers", []) if not l.get("ran")]
    n_err = sum(len(l.get("errors", [])) for l in report.get("layers", []))
    if report.get("valid") is True:
        text = "Gültig: Die Datei hat alle ausgeführten Pflichtprüfungen ohne Fehler bestanden."
    elif report.get("invalid_reason_de"):
        text = "Nicht gültig: " + report["invalid_reason_de"]
        if n_err:
            text += f" {n_err} Fehler gefunden."
    elif fmt == "unknown" and n_err == 0:
        text = "Nicht geprüft: Das Format oder Profil wurde nicht erkannt."
    else:
        text = f"Nicht gültig: {n_err} Fehler gefunden." if n_err else "Nicht gültig: Pflichtprüfungen konnten nicht ausgeführt werden."
    if skipped:
        text += " Übersprungen (nicht bestanden, sondern nicht geprüft): " + "; ".join(skipped) + "."
    if report.get("totals_warning"):
        text += " Hinweis: Die Summen weichen von den Quelldaten ab."
    return text
