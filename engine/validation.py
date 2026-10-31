"""validate(data, filename) -> Report (contracts/mapping.md).

Layers:
  XSD        UN/CEFACT CII D16B schema (engine/rules/cen/cii-xsd)
  EN16931    CEN business rules, official compiled XSLT, run with Saxon HE,
             plus BR-CO-25 which the pinned CEN CII stylesheet does not contain
  XRechnung  KoSIT national rules (BR-DE-*), only for the XRechnung profile
  KoSIT      the official KoSIT validator, only when KOSIT_VALIDATOR_JAR is set

Input is untrusted: size limit 5 MB, no DTD/entities/network, DOCTYPE rejected,
and only the re-serialised safe tree is handed to Saxon. Nothing about the file
content is logged.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import threading
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

from lxml import etree

from .messages_de import message_for

RULES = Path(__file__).resolve().parent / "rules"
CII_XSD = RULES / "cen/cii-xsd/CrossIndustryInvoice_100pD16B.xsd"
CEN_XSLT = RULES / "cen/EN16931-CII-validation.xslt"
XR_SCH = RULES / "xrechnung/XRechnung-CII-validation.sch"
XR_XSLT = RULES / "XRechnung-CII-validation.xslt"

MAX_BYTES = 5 * 1024 * 1024
SVRL = "{http://purl.oclc.org/dsdl/svrl}"
CII_NS = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
UBL_NS = ("urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
          "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2")
VARL = "{http://www.xoev.de/de/validator/varl/1}"
LAYER_NAMES = ("XSD", "EN16931", "XRechnung", "KoSIT")
KOSIT_MISSING = "KoSIT-Prüfer nicht installiert"


# ---------------------------------------------------------------- report helpers

def _layer(name, ran=True, skipped_reason=None, errors=None, warnings=None) -> dict:
    return {"name": name, "ran": ran, "skipped_reason": skipped_reason,
            "errors": errors or [], "warnings": warnings or []}


def _issue(rule_id, text, location=None) -> dict:
    text = " ".join((text or "").split())[:500]
    return {"id": rule_id, "message_de": message_for(rule_id, text), "text_en": text, "location": location}


def _split(issues: list[tuple[str, dict]]) -> tuple[list, list]:
    """(flag, issue) -> errors, warnings; deduplicated on (id, location)."""
    errors, warnings, seen = [], [], set()
    for flag, issue in issues:
        key = (issue["id"], issue["location"])
        if key in seen:
            continue
        seen.add(key)
        (warnings if (flag or "fatal").lower() in ("warning", "information", "info") else errors).append(issue)
    return errors, warnings


def is_valid(layers: list[dict], profile: str, app_env: str | None = None) -> bool:
    """Validity rule of contracts/mapping.md."""
    env = (app_env if app_env is not None else os.environ.get("APP_ENV", "dev")).lower()
    by = {layer["name"]: layer for layer in layers}
    required = ["XSD", "EN16931"]
    if profile == "xrechnung":
        required.append("XRechnung")
    if env in ("staging", "prod"):
        required.append("KoSIT")
    return all(n in by and by[n]["ran"] and not by[n]["errors"] for n in required)


def _report(profile, layers, app_env=None) -> dict:
    return {"valid": is_valid(layers, profile, app_env), "profile": profile, "layers": layers, "totals_warning": None}


def _input_error_report(rule_id: str, text_en: str, skip_reason: str) -> dict:
    layers = [_layer("XSD", ran=True, errors=[_issue(rule_id, text_en)])]
    layers += [_layer(n, ran=False, skipped_reason=skip_reason) for n in LAYER_NAMES[1:]]
    return _report("unknown", layers)


# ---------------------------------------------------------------- parsing

def _safe_parser() -> etree.XMLParser:
    return etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False, load_dtd=False,
                           dtd_validation=False, remove_pis=False)


def parse_untrusted(data: bytes) -> etree._ElementTree:
    """Parse XML safely. Raises ValueError("XML-DOCTYPE") or etree.XMLSyntaxError."""
    tree = etree.ElementTree(etree.fromstring(data, parser=_safe_parser()))
    info = tree.docinfo
    if info.doctype or info.internalDTD is not None or info.externalDTD is not None or b"<!DOCTYPE" in data[:4096].upper():
        raise ValueError("XML-DOCTYPE")
    return tree


def _extract_pdf_xml(data: bytes) -> bytes | None:
    from facturx import get_xml_from_pdf

    _name, xml = get_xml_from_pdf(data, check_xsd=False)
    return xml or None


def detect_profile(root: etree._Element) -> str:
    ids = root.xpath("/*/*[local-name()='ExchangedDocumentContext']/*[local-name()='GuidelineSpecifiedDocumentContextParameter']/*[local-name()='ID']/text()")
    gid = (ids[0] if ids else "").strip()
    if "xeinkauf.de:kosit:xrechnung" in gid or "xeinkauf.de:kosit:extension:xrechnung" in gid:
        return "xrechnung"
    if gid.startswith("urn:cen.eu:en16931:2017") or "factur-x" in gid or "zugferd" in gid.lower():
        return "zugferd"
    return "unknown"


# ---------------------------------------------------------------- layers

@lru_cache(maxsize=1)
def _xsd() -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(CII_XSD)))


_saxon_lock = threading.Lock()
_saxon: dict = {}


def _xslt(path: Path):
    """Compiled Saxon executable, cached per process (compiling CEN takes seconds)."""
    from saxonche import PySaxonProcessor

    if "proc" not in _saxon:
        _saxon["proc"] = PySaxonProcessor(license=False)
    key = str(path)
    if key not in _saxon:
        _saxon[key] = _saxon["proc"].new_xslt30_processor().compile_stylesheet(stylesheet_file=key)
    return _saxon["proc"], _saxon[key]


def _run_xslt(path: Path, xml_text: str) -> etree._Element:
    with _saxon_lock:
        proc, exe = _xslt(path)
        node = proc.parse_xml(xml_text=xml_text)
        out = exe.transform_to_string(xdm_node=node)
    if not out:
        raise RuntimeError(f"{path.name} produced no output")
    return etree.fromstring(out.encode("utf-8"), parser=_safe_parser())


def _svrl_issues(svrl: etree._Element) -> list[tuple[str, dict]]:
    out = []
    for fa in svrl.iter(f"{SVRL}failed-assert", f"{SVRL}successful-report"):
        text = " ".join("".join(fa.itertext()).split())
        out.append((fa.get("flag") or "fatal", _issue(fa.get("id"), text, fa.get("location"))))
    return out


def layer_xsd(tree) -> dict:
    schema = _xsd()
    if schema.validate(tree):
        return _layer("XSD")
    issues = [("fatal", _issue("XSD", e.message, e.path)) for e in schema.error_log]
    errors, warnings = _split(issues)
    return _layer("XSD", errors=errors, warnings=warnings)


def _br_co_25(root) -> list[tuple[str, dict]]:
    """BR-CO-25 (EN 16931): amount due > 0 requires BT-9 or BT-20.

    Not contained in the pinned CEN CII stylesheet 1.3.17; checked here with the
    rule's original wording. Marked as engine supplement in the text.
    """
    ns = {"ram": RAM}
    for st in root.iter(f"{{{RAM}}}ApplicableHeaderTradeSettlement"):
        due = st.xpath("ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:DuePayableAmount/text()", namespaces=ns)
        try:
            positive = bool(due) and Decimal(due[0].strip()) > 0
        except InvalidOperation:
            positive = False
        has = st.xpath("ram:SpecifiedTradePaymentTerms[ram:DueDateDateTime or normalize-space(ram:Description) != '']",
                       namespaces=ns)
        if positive and not has:
            text = ("[BR-CO-25]-In case the Amount due for payment (BT-115) is positive, either the Payment due date "
                    "(BT-9) or the Payment terms (BT-20) shall be present. (engine supplement: rule missing in "
                    "pinned CEN CII stylesheet)")
            return [("fatal", _issue("BR-CO-25", text, etree.ElementTree(root).getpath(st)))]
    return []


def layer_cen(xml_text: str, root) -> dict:
    svrl = _run_xslt(CEN_XSLT, xml_text)
    if not any(True for _ in svrl.iter(f"{SVRL}fired-rule")):
        raise RuntimeError("CEN rules fired on no element")
    errors, warnings = _split(_svrl_issues(svrl) + _br_co_25(root))
    return _layer("EN16931", errors=errors, warnings=warnings)


def _ensure_xr_xslt() -> None:
    if not XR_XSLT.exists():
        from .sch2xslt import compile_schema

        XR_XSLT.write_text(compile_schema(XR_SCH), encoding="utf-8")


def layer_xrechnung(xml_text: str) -> dict:
    _ensure_xr_xslt()
    errors, warnings = _split(_svrl_issues(_run_xslt(XR_XSLT, xml_text)))
    return _layer("XRechnung", errors=errors, warnings=warnings)


def parse_kosit_report(report_xml: bytes) -> tuple[list, list, bool]:
    """Parse a KoSIT VARL report -> (errors, warnings, accepted)."""
    root = etree.fromstring(report_xml, parser=_safe_parser())
    issues = []
    for m in root.iter(f"{VARL}message"):
        rule_id = m.get("code") or m.get("id")
        level = (m.get("level") or "error").lower()
        issues.append(("warning" if level in ("warning", "information") else "fatal",
                       _issue(rule_id, "".join(m.itertext()), m.get("xpathLocation"))))
    accepted = root.find(f".//{VARL}assessment/{VARL}accept") is not None
    errors, warnings = _split(issues)
    if not accepted and not errors:
        errors.append(_issue("KOSIT-REJECT", "KoSIT validator did not accept the document (no scenario or reject)."))
    return errors, warnings, accepted


def layer_kosit(xml_bytes: bytes) -> dict:
    jar = os.environ.get("KOSIT_VALIDATOR_JAR")
    if not jar:
        return _layer("KoSIT", ran=False, skipped_reason=KOSIT_MISSING)
    jar_path = Path(jar)
    config = Path(os.environ.get("KOSIT_CONFIG_DIR") or jar_path.parent)
    scenarios = config / "scenarios.xml"
    if not jar_path.is_file() or not scenarios.is_file():
        return _layer("KoSIT", ran=False,
                      skipped_reason="KoSIT-Prüfer nicht vollständig installiert (Programm oder XRechnung-Konfiguration fehlt)")
    with tempfile.TemporaryDirectory(prefix="kosit-") as tmp:
        src = Path(tmp) / "invoice.xml"
        src.write_bytes(xml_bytes)
        out_dir = Path(tmp) / "out"
        out_dir.mkdir()
        try:
            subprocess.run(["java", "-jar", str(jar_path), "-s", str(scenarios), "-r", str(config),
                            "-o", str(out_dir), str(src)],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return _layer("KoSIT", ran=False, skipped_reason=f"KoSIT-Prüfer konnte nicht ausgeführt werden ({type(exc).__name__})")
        report = out_dir / "invoice-report.xml"
        if not report.is_file():
            return _layer("KoSIT", ran=False, skipped_reason="KoSIT-Prüfer lieferte keinen Bericht")
        errors, warnings, _accepted = parse_kosit_report(report.read_bytes())
    return _layer("KoSIT", errors=errors, warnings=warnings)


def _guarded(name: str, fn, *args) -> dict:
    try:
        return fn(*args)
    except Exception as exc:  # a layer that cannot run is shown as not run, never as passed
        return _layer(name, ran=False, skipped_reason=f"Prüfschicht konnte nicht ausgeführt werden ({type(exc).__name__})")


# ---------------------------------------------------------------- entry point

def validate(data: bytes, filename: str = "") -> dict:
    """Validate an e-invoice (CII XML, or PDF with embedded CII). Returns a Report dict."""
    not_run = "Vorherige Prüfung fehlgeschlagen: keine lesbare E-Rechnung"
    if not data:
        return _input_error_report("FILE-EMPTY", "Empty file.", not_run)
    if len(data) > MAX_BYTES:
        return _input_error_report("FILE-TOO-LARGE", f"File exceeds {MAX_BYTES} bytes.", not_run)

    if data.lstrip()[:5] == b"%PDF-":
        try:
            xml = _extract_pdf_xml(data)
        except Exception:
            return _input_error_report("PDF-UNREADABLE", "PDF could not be read.", not_run)
        if not xml:
            return _input_error_report("PDF-NO-XML", "No embedded invoice XML found in PDF.", not_run)
        if len(xml) > MAX_BYTES:
            return _input_error_report("FILE-TOO-LARGE", f"Embedded XML exceeds {MAX_BYTES} bytes.", not_run)
        data = xml

    try:
        tree = parse_untrusted(data)
    except ValueError:
        return _input_error_report("XML-DOCTYPE", "DOCTYPE declarations are not accepted.", not_run)
    except etree.XMLSyntaxError:
        return _input_error_report("XML-NOT-WELLFORMED", "XML is not well-formed.", not_run)

    root = tree.getroot()
    ns = etree.QName(root).namespace
    if ns in UBL_NS:
        reason = "UBL-Format wird in dieser Version nicht geprüft (nur UN/CEFACT CII)"
        layers = [_layer(n, ran=False, skipped_reason=reason) for n in LAYER_NAMES]
        return _report("unknown", layers)
    if ns != CII_NS:
        return _input_error_report("FORMAT-UNKNOWN", "Root element is neither CII nor UBL.", not_run)

    profile = detect_profile(root)
    xml_text = etree.tostring(root, encoding="unicode")
    layers = [_guarded("XSD", layer_xsd, tree), _guarded("EN16931", layer_cen, xml_text, root)]
    if profile == "xrechnung":
        layers.append(_guarded("XRechnung", layer_xrechnung, xml_text))
    else:
        layers.append(_layer("XRechnung", ran=False,
                             skipped_reason="Kein XRechnung-Profil (BT-24); XRechnung-Regeln nicht anwendbar"))
    layers.append(_guarded("KoSIT", layer_kosit, etree.tostring(root, xml_declaration=True, encoding="UTF-8")))
    return _report(profile, layers)
