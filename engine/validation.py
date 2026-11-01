"""validate(data, filename) -> Report (contracts/mapping.md).

Layers:
  XSD        UN/CEFACT CII D16B schema (engine/rules/cen/cii-xsd)
  EN16931    CEN business rules, official compiled XSLT, run with Saxon HE,
             plus BR-CO-25 which the pinned CEN CII stylesheet does not contain
  XRechnung  KoSIT national rules (BR-DE-*), only for the XRechnung profile
  KoSIT      the official KoSIT validator, only when KOSIT_VALIDATOR_JAR is set; at most
             KOSIT_MAX_PARALLEL JVMs per process; validate_many() checks a batch in one JVM run
  PDF/A      only for PDF input: PDF/A-3 via Mustang when MUSTANG_JAR is set, else shown as skipped
             (never counted as passed; errors from a run make the file invalid)

The specification identifier (BT-24) must be recognised and EN 16931 compliant: unknown ids,
MINIMUM and BASIC-WL are never valid. The Report carries `guideline_id` (contract addition).

Input is untrusted: size limit 5 MB, no DTD/entities/network, DOCTYPE rejected,
and only the re-serialised safe tree is handed to Saxon. Nothing about the file
content is logged.
"""
from __future__ import annotations

import os
import re
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
PDFA_SKIPPED = "PDF/A-3-Konformität nicht geprüft"
KOSIT_MAX_PARALLEL_DEFAULT = 2
KOSIT_BATCH_MAX = 200          # files per KoSIT JVM run
KOSIT_TIMEOUT_BASE = 120       # seconds per JVM run ...
KOSIT_TIMEOUT_PER_FILE = 2     # ... plus per file
KOSIT_TIMEOUT_MAX = 1800


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
    """Validity rule of contracts/mapping.md, plus: the profile must be recognised.

    Profile "unknown" is never valid. A recognised but non-compliant guideline (MINIMUM, BASIC-WL) carries a
    PROFILE-NOT-EINVOICE error in the EN16931 layer, so it fails through the layer check.
    """
    if profile not in ("xrechnung", "zugferd"):
        return False
    env = (app_env if app_env is not None else os.environ.get("APP_ENV", "dev")).lower()
    by = {layer["name"]: layer for layer in layers}
    required = ["XSD", "EN16931"]
    if profile == "xrechnung":
        required.append("XRechnung")
    if env in ("staging", "prod"):
        required.append("KoSIT")
    if any(layer["ran"] and layer["errors"] for layer in layers if layer["name"] == "PDF/A"):
        return False  # a PDF/A check that ran and failed always counts; a skipped one is shown, never passed
    return all(n in by and by[n]["ran"] and not by[n]["errors"] for n in required)


def _report(profile, layers, app_env=None, guideline: str | None = None) -> dict:
    """Report dict. `guideline_id` (BT-24 as found, or None) is a contract addition (docs/requests/engine.md)."""
    return {"valid": is_valid(layers, profile, app_env), "profile": profile, "guideline_id": guideline,
            "layers": layers, "totals_warning": None}


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


BMF_SOURCE = ("https://www.ihk.de/blueprint/servlet/resource/blob/6287096/b75ea97a08683f14991b4315c44fee1c/"
              "bmf-schreiben-15-10-2024-e-rechnung-data.pdf")
_VER = r"\d+(?:\.\d+)*"
# XRechnung base id, optionally followed by the official extension or CVD suffix (as used in the KoSIT test suite).
_XR_RE = re.compile(
    r"^urn:cen\.eu:en16931:2017#compliant#urn:xeinkauf\.de:kosit:xrechnung_" + _VER
    + r"(?:#conformant#urn:xeinkauf\.de:kosit:extension:xrechnung_" + _VER
    + r"|#compliant#urn:xeinkauf\.de:kosit:xrechnung:cvd_" + _VER + r")?$")
# Factur-X / ZUGFeRD 2.x guideline ids (BT-24). BASIC is a CIUS of EN 16931 and counts as an E-Rechnung
# (BMF 15.10.2024 excludes only MINIMUM and BASIC-WL); EXTENDED is a conformant extension.
_FX_COMPLIANT = {
    "urn:cen.eu:en16931:2017": "EN16931",
    "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic": "BASIC",
    "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended": "EXTENDED",
    "urn:cen.eu:en16931:2017#conformant#urn:zugferd.de:2p0:extended": "EXTENDED",
}
_FX_NOT_EINVOICE = {
    "urn:factur-x.eu:1p0:minimum": "MINIMUM",
    "urn:zugferd.de:2p0:minimum": "MINIMUM",
    "urn:factur-x.eu:1p0:basicwl": "BASIC-WL",
    "urn:zugferd.de:2p0:basicwl": "BASIC-WL",
}


def guideline_id(root: etree._Element) -> str:
    """BT-24 specification identifier ("" when absent)."""
    ids = root.xpath("/*/*[local-name()='ExchangedDocumentContext']/*[local-name()='GuidelineSpecifiedDocumentContextParameter']/*[local-name()='ID']/text()")
    return (ids[0] if ids else "").strip()


def describe_guideline(gid: str) -> tuple[str, str | None, bool]:
    """BT-24 -> (profile, level, compliant).

    profile: "xrechnung" | "zugferd" | "unknown"; level: "XRECHNUNG", "EN16931", "BASIC", "EXTENDED",
    "MINIMUM", "BASIC-WL" or None; compliant: True only for a recognised EN 16931 compliant/conformant id.
    Matching is exact (no substring guesses): an unrecognised id is "unknown" and never valid.
    """
    if _XR_RE.match(gid):
        return "xrechnung", "XRECHNUNG", True
    if gid in _FX_COMPLIANT:
        return "zugferd", _FX_COMPLIANT[gid], True
    if gid in _FX_NOT_EINVOICE:
        return "zugferd", _FX_NOT_EINVOICE[gid], False
    return "unknown", None, False


def detect_profile(root: etree._Element) -> str:
    return describe_guideline(guideline_id(root))[0]


def _profile_issue(gid: str, level: str | None, compliant: bool) -> dict | None:
    """Error for a missing, unknown or non-compliant BT-24; None when the profile is fine."""
    if compliant:
        return None
    shown = " ".join(gid.split())[:120]
    if level in ("MINIMUM", "BASIC-WL"):
        return {"id": "PROFILE-NOT-EINVOICE",
                "message_de": f"Das ZUGFeRD/Factur-X-Profil {level} (BT-24) ist keine E-Rechnung im Sinne von "
                              f"§ 14 UStG, weil es nicht alle Pflichtangaben nach EN 16931 enthält. Bitte mindestens "
                              f"das Profil EN 16931 (COMFORT) oder XRechnung verwenden. Quelle: BMF-Schreiben vom "
                              f"15.10.2024, Rn. 25 und 30, {BMF_SOURCE}",
                "text_en": f"Guideline {shown} ({level}) is not EN 16931 compliant; not an e-invoice under German VAT law.",
                "location": "/rsm:CrossIndustryInvoice/rsm:ExchangedDocumentContext"}
    label = f"„{shown}“" if shown else "(keine Angabe)"
    return {"id": "PROFILE-UNKNOWN",
            "message_de": f"Unbekanntes Profil {label} (Spezifikationskennung BT-24): Die Datei ist keine "
                          f"E-Rechnung nach EN 16931, die hier geprüft werden kann. Erwartet wird z. B. "
                          f"XRechnung 3.0 oder ZUGFeRD/Factur-X EN 16931.",
            "text_en": f"Unrecognised specification identifier (BT-24): {shown or '(missing)'}.",
            "location": "/rsm:CrossIndustryInvoice/rsm:ExchangedDocumentContext"}


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


def _kosit_setup() -> tuple[Path, Path, Path] | dict:
    """(jar, config dir, scenarios.xml) or a skipped KoSIT layer."""
    jar = os.environ.get("KOSIT_VALIDATOR_JAR")
    if not jar:
        return _layer("KoSIT", ran=False, skipped_reason=KOSIT_MISSING)
    jar_path = Path(jar)
    config = Path(os.environ.get("KOSIT_CONFIG_DIR") or jar_path.parent)
    scenarios = config / "scenarios.xml"
    if not jar_path.is_file() or not scenarios.is_file():
        return _layer("KoSIT", ran=False,
                      skipped_reason="KoSIT-Prüfer nicht vollständig installiert (Programm oder XRechnung-Konfiguration fehlt)")
    return jar_path, config, scenarios


_kosit_sem_lock = threading.Lock()
_kosit_sem: dict = {}


def kosit_semaphore() -> threading.BoundedSemaphore:
    """Process-wide cap on parallel KoSIT JVMs (env KOSIT_MAX_PARALLEL, default 2, read once)."""
    with _kosit_sem_lock:
        if "sem" not in _kosit_sem:
            try:
                n = int(os.environ.get("KOSIT_MAX_PARALLEL") or KOSIT_MAX_PARALLEL_DEFAULT)
            except ValueError:
                n = KOSIT_MAX_PARALLEL_DEFAULT
            _kosit_sem["sem"] = threading.BoundedSemaphore(max(1, n))
        return _kosit_sem["sem"]


def _kosit_timeout(n_files: int) -> int:
    return min(KOSIT_TIMEOUT_MAX, KOSIT_TIMEOUT_BASE + KOSIT_TIMEOUT_PER_FILE * n_files)


def layer_kosit_many(xml_list: list[bytes]) -> list[dict]:
    """KoSIT layer for several documents with ONE JVM run per chunk of KOSIT_BATCH_MAX files.

    The KoSIT CLI takes several input files and writes `<name>-report.xml` for each. Runs are
    bounded process-wide by kosit_semaphore(). A document without a report gets a skipped layer.
    """
    if not xml_list:
        return []
    setup = _kosit_setup()
    if isinstance(setup, dict):
        return [dict(setup) for _ in xml_list]
    jar_path, config, scenarios = setup
    out: list[dict] = []
    for start in range(0, len(xml_list), KOSIT_BATCH_MAX):
        chunk = xml_list[start:start + KOSIT_BATCH_MAX]
        with tempfile.TemporaryDirectory(prefix="kosit-") as tmp:
            names = [f"invoice-{i:04d}" for i in range(len(chunk))]
            srcs = []
            for name, xml_bytes in zip(names, chunk):
                src = Path(tmp) / f"{name}.xml"
                src.write_bytes(xml_bytes)
                srcs.append(str(src))
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()
            try:
                with kosit_semaphore():
                    subprocess.run(["java", "-jar", str(jar_path), "-s", str(scenarios), "-r", str(config),
                                    "-o", str(out_dir), *srcs],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=_kosit_timeout(len(chunk)), check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                reason = f"KoSIT-Prüfer konnte nicht ausgeführt werden ({type(exc).__name__})"
                out.extend(_layer("KoSIT", ran=False, skipped_reason=reason) for _ in chunk)
                continue
            for name in names:
                report = out_dir / f"{name}-report.xml"
                if not report.is_file():
                    out.append(_layer("KoSIT", ran=False, skipped_reason="KoSIT-Prüfer lieferte keinen Bericht"))
                    continue
                try:
                    errors, warnings, _accepted = parse_kosit_report(report.read_bytes())
                except Exception as exc:
                    out.append(_layer("KoSIT", ran=False,
                                      skipped_reason=f"KoSIT-Bericht nicht lesbar ({type(exc).__name__})"))
                    continue
                out.append(_layer("KoSIT", errors=errors, warnings=warnings))
    return out


def layer_kosit(xml_bytes: bytes) -> dict:
    return layer_kosit_many([xml_bytes])[0]


# ---------------------------------------------------------------- PDF/A (PDF input only)

def _mustang_pdf_section(stdout: bytes) -> tuple[str | None, list[str]]:
    """(status of the PDF part, error texts) from Mustang's validation XML; status None if not found."""
    m = re.search(rb"<validation\b.*</validation>", stdout or b"", re.S)
    if not m:
        return None, []
    root = etree.fromstring(m.group(0), parser=_safe_parser())
    pdf = root.find("pdf")
    if pdf is None:
        return None, []
    summary = pdf.find("summary")
    status = summary.get("status") if summary is not None else None
    errors = [" ".join("".join(e.itertext()).split()) for e in pdf.iter("error")]
    return status, [e for e in errors if e][:20]


def layer_pdfa(pdf_bytes: bytes) -> dict:
    """PDF/A-3 conformance of an uploaded PDF: Mustang when MUSTANG_JAR is set, else visibly skipped."""
    jar = os.environ.get("MUSTANG_JAR")
    if not jar or not Path(jar).is_file():
        return _layer("PDF/A", ran=False, skipped_reason=PDFA_SKIPPED)
    with tempfile.TemporaryDirectory(prefix="pdfa-") as tmp:
        (Path(tmp) / "in.pdf").write_bytes(pdf_bytes)
        try:
            r = subprocess.run(["java", "-jar", jar, "--action", "validate", "--source", "in.pdf"], cwd=tmp,
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return _layer("PDF/A", ran=False, skipped_reason=f"{PDFA_SKIPPED} (Mustang: {type(exc).__name__})")
    try:
        status, texts = _mustang_pdf_section(r.stdout)
    except etree.XMLSyntaxError:
        status, texts = None, []
    if status == "valid":
        return _layer("PDF/A")
    if status == "invalid":
        errors = [_issue("PDFA-3", t) for t in texts] or [_issue("PDFA-3", "PDF/A-3 validation failed (Mustang).")]
        return _layer("PDF/A", errors=errors)
    return _layer("PDF/A", ran=False, skipped_reason=f"{PDFA_SKIPPED} (Mustang lieferte kein Ergebnis)")


def _guarded(name: str, fn, *args) -> dict:
    try:
        return fn(*args)
    except Exception as exc:  # a layer that cannot run is shown as not run, never as passed
        return _layer(name, ran=False, skipped_reason=f"Prüfschicht konnte nicht ausgeführt werden ({type(exc).__name__})")


# ---------------------------------------------------------------- entry points

class _Prepared:
    """Local layers done; KoSIT (and finishing) still to do."""

    def __init__(self, profile, gid, layers, kosit_xml, pdfa):
        self.profile, self.gid, self.layers, self.kosit_xml, self.pdfa = profile, gid, layers, kosit_xml, pdfa

    def finish(self, kosit_layer: dict) -> dict:
        layers = self.layers + [kosit_layer] + ([self.pdfa] if self.pdfa else [])
        return _report(self.profile, layers, guideline=self.gid or None)


def _prepare(data: bytes) -> dict | _Prepared:
    """Parse and run XSD/EN16931/XRechnung (and PDF/A for PDFs). Returns a final Report on input errors."""
    not_run = "Vorherige Prüfung fehlgeschlagen: keine lesbare E-Rechnung"
    if not data:
        return _input_error_report("FILE-EMPTY", "Empty file.", not_run)
    if len(data) > MAX_BYTES:
        return _input_error_report("FILE-TOO-LARGE", f"File exceeds {MAX_BYTES} bytes.", not_run)

    pdfa = None
    if data.lstrip()[:5] == b"%PDF-":
        def pdf_error(rule_id, text):
            rep = _input_error_report(rule_id, text, not_run)
            rep["layers"].append(_layer("PDF/A", ran=False, skipped_reason=PDFA_SKIPPED))
            return rep
        try:
            xml = _extract_pdf_xml(data)
        except Exception:
            return pdf_error("PDF-UNREADABLE", "PDF could not be read.")
        if not xml:
            return pdf_error("PDF-NO-XML", "No embedded invoice XML found in PDF.")
        if len(xml) > MAX_BYTES:
            return pdf_error("FILE-TOO-LARGE", f"Embedded XML exceeds {MAX_BYTES} bytes.")
        pdfa = _guarded("PDF/A", layer_pdfa, data)
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

    gid = guideline_id(root)
    profile, level, compliant = describe_guideline(gid)
    xml_text = etree.tostring(root, encoding="unicode")
    cen = _guarded("EN16931", layer_cen, xml_text, root)
    problem = _profile_issue(gid, level, compliant)
    if problem:
        cen["errors"].insert(0, problem)
    layers = [_guarded("XSD", layer_xsd, tree), cen]
    if profile == "xrechnung":
        layers.append(_guarded("XRechnung", layer_xrechnung, xml_text))
    else:
        layers.append(_layer("XRechnung", ran=False,
                             skipped_reason="Kein XRechnung-Profil (BT-24); XRechnung-Regeln nicht anwendbar"))
    return _Prepared(profile, gid, layers, etree.tostring(root, xml_declaration=True, encoding="UTF-8"), pdfa)


def validate(data: bytes, filename: str = "") -> dict:
    """Validate an e-invoice (CII XML, or PDF with embedded CII). Returns a Report dict."""
    prep = _prepare(data)
    if isinstance(prep, dict):
        return prep
    return prep.finish(_guarded("KoSIT", layer_kosit, prep.kosit_xml))


def validate_many(items: list[tuple[bytes, str]]) -> list[dict]:
    """validate() for several files, with one KoSIT JVM run for the whole batch. Same order as `items`."""
    prepared = [_prepare(data) for data, _name in items]
    todo = [p for p in prepared if isinstance(p, _Prepared)]
    try:
        kosit = layer_kosit_many([p.kosit_xml for p in todo])
    except Exception as exc:
        reason = f"Prüfschicht konnte nicht ausgeführt werden ({type(exc).__name__})"
        kosit = [_layer("KoSIT", ran=False, skipped_reason=reason) for _ in todo]
    it = iter(kosit)
    return [p.finish(next(it)) if isinstance(p, _Prepared) else p for p in prepared]
