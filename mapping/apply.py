"""apply: Table + Mapping + seller profile -> invoice dicts (contracts/invoice.schema.json) and RowErrors.

Invoices that have any RowError are NOT returned; their errors are. Cell text is trimmed
before transforms. Nothing in here logs cell values.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from contracts.types import RowError, Table

from .countries import country_code
from .targets import (
    ALLOWED_TARGETS, DATE_TARGETS, GERMAN_LABELS, MONEY_TARGETS, SIGNED_LINE_TARGETS, TRANSFORMS,
    invoice_schema, is_line_target,
)
from .transforms import (
    SIMPLE, TransformError, UNIT_CODES, date_iso, format_decimal, gross_to_net, parse_decimal, rate_to_category, unit_map,
)

VAT_CATEGORIES = {"S", "Z", "E", "AE", "K", "G", "O"}
EXEMPT_CATEGORIES = {"E", "AE", "K", "G", "O"}
EAS_SCHEMES = {"EM", "0204", "9930", "0088"}


class MappingError(ValueError):
    """The mapping itself is invalid (unknown target/transform/column). `message_de` is safe to show."""

    def __init__(self, message_de: str):
        super().__init__(message_de)
        self.message_de = message_de


# ------------------------------------------------------------------ mapping validation

def validate_mapping(mapping: dict, columns: list[str] | None = None) -> list[str]:
    """Return German problems with a mapping (empty list = OK). Used by apply and the AI provider."""
    problems: list[str] = []
    if not isinstance(mapping, dict):
        return ["Zuordnung ist kein Objekt"]
    grouping = mapping.get("grouping") or {}
    if not isinstance(grouping, dict) or grouping.get("mode") not in ("row_per_invoice", "row_per_line"):
        problems.append("grouping.mode muss 'row_per_invoice' oder 'row_per_line' sein")
    gcol = grouping.get("invoice_number_column") if isinstance(grouping, dict) else None
    if gcol is not None and columns is not None and gcol not in columns:
        problems.append(f"Spalte '{gcol}' für die Rechnungsnummer existiert nicht")
    fields = mapping.get("fields")
    if not isinstance(fields, list):
        return problems + ["fields fehlt oder ist keine Liste"]
    seen: set[str] = set()
    for i, f in enumerate(fields):
        if not isinstance(f, dict):
            problems.append(f"Feld {i + 1} ist kein Objekt")
            continue
        t = f.get("target")
        if t not in ALLOWED_TARGETS:
            problems.append(f"Ziel '{t}' ist nicht erlaubt")
            continue
        if t in seen:
            problems.append(f"Ziel '{t}' ist mehrfach zugeordnet")
        seen.add(t)
        has_src = f.get("source_column") is not None
        has_const = f.get("constant") is not None
        if has_src == has_const:
            problems.append(f"Ziel '{t}': genau eines von source_column oder constant angeben")
        if has_src and columns is not None and f["source_column"] not in columns:
            problems.append(f"Ziel '{t}': Spalte '{f['source_column']}' existiert nicht")
        if has_const and not isinstance(f["constant"], str):
            problems.append(f"Ziel '{t}': constant muss Text sein")
        tr = f.get("transform", [])
        if not isinstance(tr, list) or any(x not in TRANSFORMS for x in tr):
            problems.append(f"Ziel '{t}': unbekannte Transformation")
        if "gross_to_net" in (tr or []) and t != "/lines/*/net_price":
            problems.append(f"Ziel '{t}': gross_to_net nur für den Einzelpreis")
        conf = f.get("confidence", 1.0)
        if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
            problems.append(f"Ziel '{t}': confidence muss zwischen 0 und 1 liegen")
        if t.startswith("/seller"):
            problems.append("Verkäuferfelder dürfen nicht zugeordnet werden")
    return problems


# ------------------------------------------------------------------ per-cell evaluation

@dataclass
class Value:
    value: str | None = None
    negative: bool = False
    gross: bool = False          # gross_to_net still pending
    error: RowError | None = None


def _label(target: str) -> str:
    return GERMAN_LABELS.get(target, target)


def _err(row: int, column: str | None, target: str, code: str, msg: str) -> RowError:
    return RowError(row=row, column=column, field=target, code=code,
                    message_de=f"Zeile {row}: {_label(target)} {msg}")


def _eval(f: dict, row: list[str], rownum: int, col_index: dict[str, int], defaults: dict) -> Value:
    target = f["target"]
    column = f.get("source_column")
    if column is not None:
        raw = row[col_index[column]].strip() if col_index[column] < len(row) else ""
    else:
        raw = str(f["constant"]).strip()
    if raw == "":
        return Value(None)
    v = raw
    negative = False
    gross = False
    has_abs = False
    try:
        for t in f.get("transform", []):
            if t == "gross_to_net":
                gross = True
                continue
            if t == "rate_to_category":
                v = rate_to_category(v, defaults.get("vat_category", "S"))
                continue
            if t == "abs":
                has_abs = True
                if v.startswith("-"):
                    negative = True
            v = SIMPLE[t](v)
        v = _normalise(target, v)
    except TransformError as exc:
        return Value(error=_err(rownum, column, target, exc.code, exc.message_de))
    if target in MONEY_TARGETS and v.startswith("-"):
        if has_abs:
            v, negative = v[1:], True
        else:
            hint = " (für Gutschriften die Transformation 'abs' wählen)" if target in SIGNED_LINE_TARGETS or target.startswith("/source") else ""
            return Value(error=_err(rownum, column, target, "negative_amount", f"'{raw}' ist negativ{hint}"))
    return Value(v, negative=negative, gross=gross)


def _normalise(target: str, v: str) -> str:
    if target in MONEY_TARGETS:
        d = parse_decimal(v)
        if target == "/lines/*/quantity" or target == "/lines/*/vat_rate":
            return format_decimal(d)
        return format_decimal(d, min_places=2)
    if target in DATE_TARGETS:
        return date_iso(v)
    if target == "/buyer/country":
        code = country_code(v)
        if not code:
            raise TransformError("buyer_address_missing", f"'{v}' ist kein erkanntes Land (ISO-Code wie DE erwartet)")
        return code
    if target == "/lines/*/unit":
        return v.upper() if v.upper() in UNIT_CODES else unit_map(v)
    if target == "/lines/*/vat_category":
        if v.upper() not in VAT_CATEGORIES:
            raise TransformError("missing_required", f"'{v}' ist keine gültige Steuerkategorie (S, Z, E, AE, K, G, O)")
        return v.upper()
    if target == "/buyer/electronic_address_scheme":
        if v.upper() not in EAS_SCHEMES:
            raise TransformError("missing_required", f"'{v}' ist kein unterstütztes Adressschema (EM, 0204, 9930, 0088)")
        return v.upper()
    if target == "/currency":
        if v.upper() in ("€", "EUR", "EURO"):
            return "EUR"
        raise TransformError("missing_required", f"'{v}' wird nicht unterstützt (nur EUR)")
    return v


# ------------------------------------------------------------------ helpers

def _set(obj: dict, pointer: str, value) -> None:
    parts = pointer.strip("/").split("/")
    for p in parts[:-1]:
        obj = obj.setdefault(p, {})
    obj[parts[-1]] = value


def _get(obj: dict, pointer: str):
    for p in pointer.strip("/").split("/"):
        if not isinstance(obj, dict) or p not in obj:
            return None
        obj = obj[p]
    return obj


@dataclass
class Group:
    key: str | None
    rows: list[tuple[int, list[str]]] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


def _group(table: Table, mapping: dict, num_field: dict | None, col_index: dict[str, int], defaults: dict) -> tuple[list[Group], list[RowError]]:
    mode = mapping["grouping"]["mode"]
    errors: list[RowError] = []
    groups: list[Group] = []
    by_key: dict[str, Group] = {}
    for rownum, row in zip(table.row_numbers, table.rows):
        key = None
        if num_field is not None:
            val = _eval(num_field, row, rownum, col_index, defaults)
            key = val.value
        if mode == "row_per_line":
            if key is None:
                if groups:
                    groups[-1].rows.append((rownum, row))  # continuation row without number
                    continue
                g = Group(None)
                g.rows.append((rownum, row))
                groups.append(g)
                continue
            g = by_key.get(key)
            if g is None:
                g = by_key[key] = Group(key)
                groups.append(g)
            g.rows.append((rownum, row))
        else:
            if key is not None and key in by_key:
                errors.append(_err(rownum, num_field.get("source_column") if num_field else None, "/number", "inconsistent_invoice",
                                   f"'{key}' kommt mehrfach vor; bei einer Zeile je Position bitte 'eine Zeile je Position' wählen"))
                by_key[key].errors.append(errors[-1])
                continue
            g = Group(key)
            g.rows.append((rownum, row))
            if key is not None:
                by_key[key] = g
            groups.append(g)
    return groups, errors


# ------------------------------------------------------------------ build one invoice

def _build(group: Group, header_fields: list[dict], line_fields: list[dict], mapping: dict,
           seller_profile: dict, col_index: dict[str, int]) -> tuple[dict | None, list[RowError]]:
    defaults = seller_profile.get("defaults", {}) or {}
    errors: list[RowError] = list(group.errors)
    first_row = group.rows[0][0]
    inv: dict = {"schema_version": "1"}

    # header values (first non-empty wins; disagreement -> inconsistent_invoice)
    for f in header_fields:
        chosen: tuple[int, str] | None = None
        for rownum, row in group.rows:
            val = _eval(f, row, rownum, col_index, defaults)
            if val.error:
                errors.append(val.error)
                continue
            if val.value is None:
                continue
            if chosen is None:
                chosen = (rownum, val.value)
            elif val.value != chosen[1]:
                errors.append(_err(rownum, f.get("source_column"), f["target"], "inconsistent_invoice",
                                   f"weicht von Zeile {chosen[0]} derselben Rechnung ab"))
        if chosen is not None:
            _set(inv, f["target"], chosen[1])

    if "number" not in inv and group.key is not None:
        inv["number"] = group.key

    # lines
    lines: list[dict] = []
    signs: list[tuple[int, bool]] = []
    mapped_line_targets = {f["target"] for f in line_fields}
    for rownum, row in group.rows:
        line: dict = {}
        neg = {"/lines/*/quantity": False, "/lines/*/net_price": False}
        pending_gross: str | None = None
        row_ok = True
        for f in line_fields:
            val = _eval(f, row, rownum, col_index, defaults)
            if val.error:
                errors.append(val.error)
                row_ok = False
                continue
            if val.value is None:
                continue
            key = f["target"].rsplit("/", 1)[-1]
            if f["target"] in neg:
                neg[f["target"]] = val.negative
            if val.gross:
                pending_gross = val.value
            line[key] = val.value
        # defaults from the seller profile when the mapping has no such field at all
        if "/lines/*/vat_rate" not in mapped_line_targets:
            line.setdefault("vat_rate", format_decimal(Decimal(str(defaults.get("vat_rate", "19")))))
        if "/lines/*/vat_category" not in mapped_line_targets:
            line.setdefault("vat_category", defaults.get("vat_category", "S"))
        if "/lines/*/unit" not in mapped_line_targets and defaults.get("unit"):
            line.setdefault("unit", defaults["unit"])
        if pending_gross is not None:
            if "vat_rate" in line:
                line["net_price"] = gross_to_net(pending_gross, line["vat_rate"])
            else:
                errors.append(_err(rownum, None, "/lines/*/net_price", "missing_required",
                                   "kann ohne Steuersatz nicht von brutto in netto umgerechnet werden"))
                row_ok = False
        if not row_ok:
            continue
        if not any(k in line for k in ("description", "quantity", "net_price")):
            continue  # row carries header data only (e.g. invoice header row in a line export)
        for req in ("description", "quantity", "net_price", "vat_rate", "vat_category"):
            if req not in line:
                t = f"/lines/*/{req}"
                col = next((f.get("source_column") for f in line_fields if f["target"] == t), None)
                errors.append(_err(rownum, col, t, "missing_required", "fehlt"))
                row_ok = False
        if not row_ok:
            continue
        if line["vat_category"] in ("S",) and Decimal(line["vat_rate"]) == 0:
            errors.append(_err(rownum, None, "/lines/*/vat_category", "missing_required",
                               "ist 'S' (Regelsteuersatz), der Steuersatz aber 0 %"))
            continue
        amount_nonzero = Decimal(line["quantity"]) != 0 and Decimal(line["net_price"]) != 0
        if amount_nonzero:
            signs.append((rownum, neg["/lines/*/quantity"] != neg["/lines/*/net_price"]))
        lines.append(line)

    # credit notes: all lines negative -> 381; mixed signs -> negative_amount
    neg_rows = [r for r, n in signs if n]
    pos_rows = [r for r, n in signs if not n]
    if neg_rows and pos_rows:
        minority = neg_rows if len(neg_rows) <= len(pos_rows) else pos_rows
        for r in minority:
            errors.append(_err(r, None, "/lines/*/net_price", "negative_amount",
                               "hat ein anderes Vorzeichen als die übrigen Positionen derselben Rechnung "
                               "(Rechnung und Gutschrift bitte getrennt erfassen)"))
    inv["type_code"] = "381" if neg_rows and not pos_rows else "380"

    # required header fields (no second message for a field whose cell already failed)
    already = {e.field for e in errors}
    n_before = len(errors)
    if not inv.get("number"):
        errors.append(_err(first_row, None, "/number", "missing_required", "fehlt"))
    if not inv.get("issue_date"):
        errors.append(_err(first_row, None, "/issue_date", "missing_required", "fehlt"))
    buyer = inv.setdefault("buyer", {})
    if not buyer.get("name"):
        errors.append(_err(first_row, None, "/buyer/name", "missing_required", "fehlt"))
    for part in ("street", "postcode", "city", "country"):
        if not buyer.get(part):
            errors.append(_err(first_row, None, f"/buyer/{part}", "buyer_address_missing", "fehlt"))
    if buyer.get("country") == "DE" and buyer.get("postcode", "").isdigit() and len(buyer["postcode"]) == 4:
        buyer["postcode"] = "0" + buyer["postcode"]  # Excel dropped the leading zero
    if not buyer.get("electronic_address"):
        errors.append(_err(first_row, None, "/buyer/electronic_address", "missing_required", "fehlt (E-Mail-Adresse oder Leitweg-ID des Kunden)"))
    elif not buyer.get("electronic_address_scheme"):
        if "@" in buyer["electronic_address"]:
            buyer["electronic_address_scheme"] = "EM"
        else:
            errors.append(_err(first_row, None, "/buyer/electronic_address_scheme", "missing_required", "fehlt"))
    if not lines and not errors:
        errors.append(_err(first_row, None, "/lines/*/description", "missing_required", "keine Position gefunden"))
    period = inv.get("period")
    if period and not ("start" in period and "end" in period):
        missing = "/period/end" if "start" in period else "/period/start"
        errors.append(_err(first_row, None, missing, "missing_required", "fehlt (Beginn und Ende angeben)"))
    errors[n_before:] = [e for e in errors[n_before:] if e.field not in already]
    prec = inv.get("preceding_invoice")
    if prec and "number" not in prec:
        inv.pop("preceding_invoice")
    if errors:
        return None, errors

    inv["lines"] = lines
    inv.setdefault("currency", "EUR")
    inv["seller"] = copy.deepcopy(seller_profile["seller"])

    # payment from profile defaults
    pd = seller_profile.get("payment_defaults", {}) or {}
    payment = inv.get("payment", {})
    out_pay: dict = {"means_code": pd.get("means_code", "58")}
    for k in ("iban", "bic", "account_name"):
        if pd.get(k):
            out_pay[k] = pd[k]
    if payment.get("terms") or pd.get("terms"):
        out_pay["terms"] = payment.get("terms") or pd["terms"]
    if payment.get("due_date"):
        out_pay["due_date"] = payment["due_date"]
    elif pd.get("payment_days") is not None:
        out_pay["due_date"] = (date.fromisoformat(inv["issue_date"]) + timedelta(days=int(pd["payment_days"]))).isoformat()
    inv["payment"] = out_pay
    if "due_date" not in out_pay and "terms" not in out_pay:
        errors.append(_err(first_row, None, "/payment/due_date", "missing_required",
                           "fehlt (keine Fälligkeit in der Datei und kein Zahlungsziel im Firmenprofil)"))
    if out_pay["means_code"] == "58" and not out_pay.get("iban"):
        errors.append(_err(first_row, None, "/payment/iban", "missing_required", "fehlt im Firmenprofil (SEPA-Überweisung)"))

    used = {l["vat_category"] for l in lines} & EXEMPT_CATEGORIES
    exemptions = (defaults.get("vat_exemptions") or {})
    if used:
        ex = {c: copy.deepcopy(exemptions[c]) for c in sorted(used) if c in exemptions}
        if ex:
            inv["vat_exemptions"] = ex

    src = inv.setdefault("source", {})
    src["row_numbers"] = [r for r, _ in group.rows]
    if mapping.get("mapping_id"):
        src["mapping_id"] = str(mapping["mapping_id"])
    if errors:
        return None, errors
    return inv, []


# ------------------------------------------------------------------ schema check

_validator = None


def schema_validator():
    global _validator
    if _validator is None:
        from jsonschema import Draft202012Validator, FormatChecker
        _validator = Draft202012Validator(invoice_schema(), format_checker=FormatChecker())
    return _validator


def _schema_errors(inv: dict, first_row: int) -> list[RowError]:
    out = []
    for e in schema_validator().iter_errors(inv):
        path = "/" + "/".join(str(p) for p in e.absolute_path)
        code = {"required": "missing_required", "format": "bad_date", "pattern": "bad_number"}.get(e.validator, "missing_required")
        out.append(RowError(row=first_row, column=None, field=path, code=code,
                            message_de=f"Zeile {first_row}: Feld '{path}' entspricht nicht dem Rechnungsmodell ({e.validator})"))
    return out


# ------------------------------------------------------------------ public

def apply(table: Table, mapping: dict, seller_profile: dict) -> tuple[list[dict], list[RowError]]:
    problems = validate_mapping(mapping, table.columns)
    if problems:
        raise MappingError("Die Zuordnung ist ungültig: " + "; ".join(problems))
    if not seller_profile or "seller" not in seller_profile:
        raise MappingError("Das Firmenprofil fehlt (Verkäuferdaten).")
    col_index = {c: i for i, c in enumerate(table.columns)}
    fields = mapping["fields"]
    header_fields = [f for f in fields if not is_line_target(f["target"])]
    line_fields = [f for f in fields if is_line_target(f["target"])]
    defaults = seller_profile.get("defaults", {}) or {}

    num_field = next((f for f in fields if f["target"] == "/number"), None)
    gcol = mapping["grouping"].get("invoice_number_column")
    if num_field is None and gcol:
        num_field = {"target": "/number", "source_column": gcol, "transform": ["strip"]}
        header_fields.append(num_field)

    groups, errors = _group(table, mapping, num_field, col_index, defaults)
    invoices: list[dict] = []
    for g in groups:
        inv, errs = _build(g, header_fields, line_fields, mapping, seller_profile, col_index)
        if inv is not None:
            schema_errs = _schema_errors(inv, g.rows[0][0])
            if schema_errs:
                errs = schema_errs
                inv = None
        errors.extend(e for e in errs if e not in errors)
        if inv is not None:
            invoices.append(inv)
    errors.sort(key=lambda e: e.row)
    return invoices, errors
