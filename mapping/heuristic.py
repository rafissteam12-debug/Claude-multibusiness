"""Heuristic mapping provider (no network): synonym dictionary + value-pattern detection."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from contracts.types import Table

from .transforms import TransformError, _DMY, _ISO, date_dmy, date_iso, looks_like_number, parse_decimal, de_decimal, en_decimal, UNIT_CODES, UNIT_MAP
from .countries import country_code

MAX_PROFILE_ROWS = 500


# ------------------------------------------------------------------ normalisation

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"})


def normalize(header: str) -> str:
    h = header.translate(_UMLAUTS).lower()
    h = h.replace("e-mail", "email").replace("e mail", "email")
    return re.sub(r"[^a-z0-9]+", " ", h).strip()


def compact(header: str) -> str:
    return normalize(header).replace(" ", "")


# ------------------------------------------------------------------ concepts

@dataclass
class Concept:
    key: str
    label_de: str
    kind: str  # id, date, text, postcode, email, country, vatid, number, rate, amount, unit, any
    syn: tuple[str, ...] = ()        # substring matches (compact form)
    exact: tuple[str, ...] = ()      # whole-header matches only
    neg: tuple[str, ...] = ()        # substrings that veto the match
    neg_end: tuple[str, ...] = ()    # endings that veto the match
    buyer_sub: tuple[str, ...] = ()  # matches after a buyer prefix ("Kd", "Kunde") is removed


_ID_ENDS = ("nr", "nummer", "no", "id", "number", "nummern")
BUYER_PREFIXES = ("rechnungsempfaenger", "empfaenger", "kunden", "kunde", "kd", "customer", "client", "buyer", "debitor", "rechnungs")

CONCEPTS: tuple[Concept, ...] = (
    Concept("number", "Rechnungsnummer", "id",
            syn=("rechnungsnummer", "rechnungsnr", "rechnungsno", "renr", "rgnr", "rechnr", "belegnummer", "belegnr",
                 "invoicenumber", "invoiceno", "invoicenr", "invoiceid", "gutschriftnummer", "gutschriftnr",
                 "dokumentnummer", "dokumentnr", "rechnungsid", "fakturanummer", "fakturanr"),
            exact=("rechnung", "nummer", "nr", "number", "no", "beleg", "invoice", "belegnr"),
            neg=("kunde", "kd", "bestell", "auftrag", "order", "ursprung", "bezug", "artikel", "steuer", "ust",
                 "customer", "leitweg", "original", "referenz", "datum", "date", "korrigiert", "vat", "pos")),
    Concept("issue_date", "Rechnungsdatum", "date",
            syn=("rechnungsdatum", "belegdatum", "redatum", "rgdatum", "rechdatum", "invoicedate", "ausstellungsdatum",
                 "issuedate", "dokumentdatum", "erstellungsdatum", "fakturadatum", "datumrechnung"),
            exact=("datum", "date", "dat"),
            neg=("liefer", "leistung", "faellig", "due", "delivery", "ursprung", "bezug", "zahl", "service", "bestell", "order", "original")),
    Concept("delivery_date", "Leistungsdatum", "date",
            syn=("leistungsdatum", "lieferdatum", "deliverydate", "servicedate", "leistungszeitpunkt", "leistungsdat", "lieferungsdatum"),
            neg=("von", "bis", "start", "ende", "end", "from")),
    Concept("due_date", "Fälligkeitsdatum", "date",
            syn=("faelligkeit", "faelligam", "faellig", "zahlbarbis", "duedate", "paymentdue", "zahlungsziel", "zahlungsdatum", "due")),
    Concept("period_start", "Leistungszeitraum Beginn", "date",
            syn=("leistungvon", "leistungszeitraumvon", "zeitraumvon", "periodstart", "servicefrom", "abrechnungszeitraumvon", "leistungsbeginn", "periodfrom"),
            exact=("von", "from")),
    Concept("period_end", "Leistungszeitraum Ende", "date",
            syn=("leistungbis", "leistungszeitraumbis", "zeitraumbis", "periodend", "serviceto", "abrechnungszeitraumbis", "leistungsende", "periodto"),
            exact=("bis", "to")),
    Concept("buyer_name", "Name des Kunden", "text",
            syn=("kundenname", "firmenname", "rechnungsempfaenger", "customername", "buyername", "clientname", "debitorname", "kdname"),
            exact=("kunde", "firma", "name", "name1", "empfaenger", "customer", "buyer", "client", "auftraggeber",
                   "unternehmen", "debitor", "company", "kundefirma", "kundename"),
            neg=("strasse", "ort", "plz", "mail", "ustid", "umsatzsteuer", "vat", "land", "referenz", "zeichen", "zusatz", "name2", "artikel", "datei", "kontakt", "ansprech"),
            neg_end=_ID_ENDS, buyer_sub=("name", "name1", "firma")),
    Concept("buyer_street", "Straße des Kunden", "text",
            syn=("strasse", "strassehausnummer", "anschrift", "adresse", "street", "addressline1", "adresszeile1", "address"),
            exact=("str",),
            neg=("mail", "plz", "ort", "zusatz", "2", "liefer", "web"),
            buyer_sub=("strasse", "str", "adresse", "anschrift", "street")),
    Concept("buyer_postcode", "PLZ des Kunden", "postcode",
            syn=("postleitzahl", "zipcode", "postcode", "postalcode", "plz"),
            exact=("zip",),
            neg=("ort", "city", "liefer"),
            buyer_sub=("plz", "zip", "postleitzahl")),
    Concept("buyer_city", "Ort des Kunden", "text",
            syn=("wohnort", "ortschaft"),
            exact=("ort", "stadt", "city", "town"),
            neg=("plz", "liefer", "leistung", "geburt"),
            buyer_sub=("ort", "stadt", "city")),
    Concept("buyer_country", "Land des Kunden", "country",
            syn=("laenderkennzeichen", "countrycode", "landiso", "laendercode"),
            exact=("land", "country", "lkz", "staat", "landcode"),
            buyer_sub=("land", "country", "lkz")),
    Concept("buyer_email", "E-Mail-Adresse des Kunden", "email",
            syn=("email", "emailadresse", "emailaddress", "rechnungsemail", "mailadresse"),
            exact=("mail",),
            neg=("absender", "verkaeufer", "seller"),
            buyer_sub=("email", "mail")),
    Concept("buyer_vat_id", "USt-IdNr. des Kunden", "vatid",
            syn=("ustid", "ustidnr", "ustidnummer", "umsatzsteuerid", "umsatzsteueridentifikationsnummer", "vatid", "vatnumber",
                 "vatno", "vatreg", "vatregistration", "uidnr", "uid"),
            buyer_sub=("ustid", "ustidnr", "vatid")),
    Concept("buyer_reference", "Käuferreferenz / Leitweg-ID", "id",
            syn=("kaeuferreferenz", "leitwegid", "leitweg", "buyerreference", "ihrzeichen", "kundenreferenz", "ihrereferenz", "buyerref"),
            exact=("referenz", "reference")),
    Concept("order_reference", "Bestellnummer", "id",
            syn=("bestellnummer", "bestellnr", "bestellung", "auftragsnummer", "auftragsnr", "ordernumber", "orderno", "orderid",
                 "ponumber", "purchaseorder", "orderreference", "ihrebestellung", "bestellref", "bestellzeichen"),
            exact=("auftrag", "order", "po"),
            neg=("datum", "date")),
    Concept("preceding_number", "Nummer der Ursprungsrechnung", "id",
            syn=("ursprungsrechnung", "bezugsrechnung", "bezugrechnung", "originalrechnung", "originalinvoice", "korrigierterechnung",
                 "zurechnung", "precedinginvoice", "referenzrechnung", "rechnungsbezug", "stornierterechnung", "korrekturzu", "bezugauf"),
            neg=("datum", "date")),
    Concept("line_id", "Positionsnummer", "id",
            syn=("positionsnummer", "posnr", "lineno", "linenumber", "lfdnr", "positionnr"),
            exact=("pos", "position", "line", "zeile", "nr pos")),
    Concept("description", "Positionsbeschreibung", "text",
            syn=("beschreibung", "bezeichnung", "artikelbezeichnung", "artikelname", "artbez", "leistungsbeschreibung", "positionstext",
                 "postext", "description", "itemdescription", "produkt", "product", "betreff", "taetigkeit", "gegenstand",
                 "warenbezeichnung", "leistung", "artikel"),
            exact=("text", "item", "titel", "subject", "service", "bez", "ware"),
            neg=("datum", "date", "zeitraum", "von", "bis", "ort", "nummer", "einheit", "menge", "preis", "price", "betrag"),
            neg_end=("nr", "no", "id", "number")),
    Concept("quantity", "Menge", "number",
            syn=("menge", "anzahl", "quantity", "stueckzahl", "stunden", "hours"),
            exact=("anz", "qty", "stk", "stck", "std", "tage", "days"),
            neg=("einheit", "preis", "price", "unit")),
    Concept("unit", "Einheit", "unit",
            syn=("einheit", "mengeneinheit", "masseinheit", "unitofmeasure", "unitcode"),
            exact=("me", "unit", "uom", "einh", "stk")),
    Concept("unit_net", "Einzelpreis netto", "number",
            syn=("einzelpreis", "nettopreis", "nettoeinzelpreis", "unitprice", "netprice", "stueckpreis", "preisjeeinheit",
                 "preisproeinheit", "preiseinheit", "stundensatz", "tagessatz", "hourlyrate", "epreis", "epnetto", "preisnetto"),
            exact=("ep", "preis", "price", "einzelpr", "satz eur"),
            neg=("brutto", "gross", "gesamt", "total", "summe", "inkl")),
    Concept("unit_gross", "Einzelpreis brutto", "number",
            syn=("einzelpreisbrutto", "epbrutto", "preisbrutto", "bruttopreis", "bruttoeinzelpreis", "unitpricegross", "grossprice",
                 "grossunitprice", "stueckpreisbrutto", "preisinklmwst", "epreisbrutto", "einzelpreisinkl"),
            neg=("gesamt", "total", "summe")),
    Concept("line_net", "Nettobetrag", "amount",
            syn=("nettobetrag", "betragnetto", "gesamtnetto", "summenetto", "nettosumme", "positionsbetrag", "netamount", "amountnet",
                 "nettowert", "gesamtpreis", "zeilenbetrag", "positionswert", "nettogesamt", "linetotal", "totalnet", "subtotal", "netto"),
            exact=("betrag", "amount", "net", "summe"),
            neg=("brutto", "gross", "mwst", "ust", "steuer", "vat", "tax", "einzel", "inkl")),
    Concept("line_gross", "Bruttobetrag", "amount",
            syn=("bruttobetrag", "betragbrutto", "gesamtbrutto", "summebrutto", "bruttosumme", "gesamtbetrag", "rechnungsbetrag",
                 "endbetrag", "grossamount", "amountgross", "totalgross", "totalamount", "zahlbetrag", "bruttowert", "brutto", "gesamtsumme"),
            exact=("gross", "total", "gesamt"),
            neg=("netto", "einzel", "preis", "price")),
    Concept("vat_amount", "Steuerbetrag", "amount",
            syn=("mwstbetrag", "ustbetrag", "steuerbetrag", "mehrwertsteuerbetrag", "umsatzsteuerbetrag", "vatamount", "taxamount", "mwsteur", "usteur"),
            exact=("mwst", "ust", "steuer", "vat", "tax", "mehrwertsteuer", "umsatzsteuer"),
            neg=("satz", "rate", "prozent", "proz", "id", "nr")),
    Concept("vat_rate", "Steuersatz", "rate",
            syn=("mwstsatz", "ustsatz", "steuersatz", "mwstprozent", "ustprozent", "ustproz", "mwstproz", "vatrate", "taxrate",
                 "vatpercent", "mehrwertsteuersatz", "umsatzsteuersatz", "steuerprozent"),
            exact=("mwst", "ust", "vat", "tax", "steuer", "prozent", "satz", "mehrwertsteuer", "umsatzsteuer"),
            neg=("betrag", "amount", "eur", "id", "nr", "summe")),
    Concept("currency", "Währung", "any",
            syn=("waehrung", "currency"),
            exact=("whg", "curr", "wahrung")),
    Concept("note", "Bemerkung", "text",
            syn=("bemerkung", "notiz", "hinweis", "kommentar", "anmerkung", "freitext"),
            exact=("note", "notes", "comment", "comments")),
    Concept("terms", "Zahlungsbedingungen", "text",
            syn=("zahlungsbedingung", "paymentterms", "konditionen", "zahlungskondition")),
)
CONCEPT_BY_KEY = {c.key: c for c in CONCEPTS}

DIRECT_TARGETS = {
    "number": "/number",
    "issue_date": "/issue_date",
    "delivery_date": "/delivery_date",
    "due_date": "/payment/due_date",
    "period_start": "/period/start",
    "period_end": "/period/end",
    "buyer_name": "/buyer/name",
    "buyer_street": "/buyer/street",
    "buyer_postcode": "/buyer/postcode",
    "buyer_city": "/buyer/city",
    "buyer_country": "/buyer/country",
    "buyer_email": "/buyer/electronic_address",
    "buyer_vat_id": "/buyer/vat_id",
    "buyer_reference": "/buyer_reference",
    "order_reference": "/order_reference",
    "preceding_number": "/preceding_invoice/number",
    "line_id": "/lines/*/id",
    "description": "/lines/*/description",
    "quantity": "/lines/*/quantity",
    "unit": "/lines/*/unit",
    "vat_rate": "/lines/*/vat_rate",
    "currency": "/currency",
    "note": "/note",
    "terms": "/payment/terms",
}


# ------------------------------------------------------------------ value profiles

PLAUSIBLE_RATES = {Decimal(x) for x in ("0", "5", "5.5", "7", "9", "10", "13", "16", "19", "20", "21", "25")}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
_IBAN = re.compile(r"^[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?$")
_VATID = re.compile(r"^(DE ?\d{9}|ATU\d{8}|[A-Z]{2}[A-Z0-9]{8,12})$")
_POSTCODE = re.compile(r"^(?:[A-Z]{1,2}-?)?\d{4,5}$|^[A-Z0-9]{2,4} ?[A-Z0-9]{3}$")


@dataclass
class Profile:
    n: int = 0
    date_dmy: float = 0.0
    date_iso: float = 0.0
    num: float = 0.0
    de: int = 0
    en: int = 0
    email: float = 0.0
    iban: float = 0.0
    vatid: float = 0.0
    postcode: float = 0.0
    country: float = 0.0
    unit: float = 0.0
    alpha: float = 0.0
    rate_like: bool = False
    negative: bool = False
    distinct: int = 0

    @property
    def date(self) -> float:
        return max(self.date_dmy, self.date_iso)


def _valid_date(v: str) -> str | None:
    try:
        if _DMY.match(v):
            date_dmy(v)
            return "dmy"
        if _ISO.match(v):
            date_iso(v)
            return "iso"
    except TransformError:
        return "bad"
    return None


def profile_column(values: list[str]) -> Profile:
    vals = [v.strip() for v in values[:MAX_PROFILE_ROWS] if v.strip()]
    p = Profile(n=len(vals), distinct=len(set(vals)))
    if not vals:
        return p
    n = len(vals)
    dmy = iso = num = email = iban = vatid = pc = country = unit = alpha = 0
    rates_ok = True
    for v in vals:
        d = _valid_date(v)
        if d in ("dmy", "bad") and _DMY.match(v):
            dmy += 1
        elif d in ("iso", "bad") and _ISO.match(v):
            iso += 1
        kind = looks_like_number(v)
        if kind and d is None:
            num += 1
            if kind == "de":
                p.de += 1
            elif kind == "en":
                p.en += 1
            try:
                dec = parse_decimal(de_decimal(v) if kind in ("de", "int", "ambiguous") else en_decimal(v))
            except TransformError:
                dec = None
            if dec is not None:
                if dec < 0:
                    p.negative = True
                if abs(dec) not in PLAUSIBLE_RATES:
                    rates_ok = False
        else:
            rates_ok = False if not v.endswith("%") else rates_ok
        if _EMAIL.match(v):
            email += 1
        compact_v = v.replace(" ", "").upper()
        if _IBAN.match(v.upper()) and len(compact_v) >= 15:
            iban += 1
        if _VATID.match(v.upper()) and any(ch.isdigit() for ch in v):
            vatid += 1
        if _POSTCODE.match(v.upper()) and any(ch.isdigit() for ch in v):
            pc += 1
        if country_code(v):
            country += 1
        if v.upper() in UNIT_CODES or v.lower() in UNIT_MAP:
            unit += 1
        if any(ch.isalpha() for ch in v):
            alpha += 1
    p.date_dmy, p.date_iso, p.num = dmy / n, iso / n, num / n
    p.email, p.iban, p.vatid, p.postcode = email / n, iban / n, vatid / n, pc / n
    p.country, p.unit, p.alpha = country / n, unit / n, alpha / n
    p.rate_like = rates_ok and p.num >= 0.8
    return p


def kind_ok(kind: str, p: Profile) -> bool:
    if p.n == 0:
        return kind in ("id", "text", "vatid", "email", "any", "date", "country", "postcode")
    if kind == "date":
        return p.date >= 0.8
    if kind == "number":
        return p.num >= 0.8
    if kind == "rate":
        return p.rate_like
    if kind == "amount":
        return p.num >= 0.8 and not (p.rate_like and p.distinct <= 3)
    if kind == "text":
        return p.alpha >= 0.5 and p.date < 0.5 and p.email < 0.5
    if kind == "postcode":
        return p.postcode >= 0.8
    if kind == "email":
        return p.email >= 0.8
    if kind == "country":
        return p.country >= 0.8
    if kind == "unit":
        return p.unit >= 0.6
    if kind == "vatid":
        return p.vatid >= 0.5
    if kind == "id":
        return p.iban < 0.5 and p.email < 0.5 and p.date < 0.5
    return True


def describe_profile(p: Profile) -> str:
    if p.n == 0:
        return "Spalte ist leer"
    if p.date_dmy >= 0.8:
        return "Werte sehen aus wie Datum (TT.MM.JJJJ)"
    if p.date_iso >= 0.8:
        return "Werte sehen aus wie Datum (JJJJ-MM-TT)"
    if p.email >= 0.8:
        return "Werte sind E-Mail-Adressen"
    if p.rate_like:
        return "Werte sind übliche Steuersätze"
    if p.num >= 0.8:
        style = "deutsches Zahlenformat" if p.de > p.en else ("englisches Zahlenformat" if p.en > p.de else "ganze Zahlen")
        return f"Werte sind Zahlen ({style})"
    if p.vatid >= 0.5:
        return "Werte sehen aus wie USt-IdNr."
    if p.country >= 0.8:
        return "Werte sind Ländernamen/-codes"
    if p.unit >= 0.6:
        return "Werte sind Mengeneinheiten"
    if p.postcode >= 0.8:
        return "Werte sehen aus wie Postleitzahlen"
    return "Werte sind Text"


# ------------------------------------------------------------------ name scoring

def name_score(header: str, c: Concept) -> tuple[float, str]:
    h = compact(header)
    if not h:
        return 0.0, ""
    if any(n in h for n in c.neg) or any(h.endswith(e) and len(h) > len(e) for e in c.neg_end):
        # buyer-prefixed headers are checked separately below (e.g. 'KdName')
        if not c.buyer_sub:
            return 0.0, ""
        neg_hit = True
    else:
        neg_hit = False
    best, match = 0.0, ""
    if not neg_hit:
        for s in c.exact:
            if h == s.replace(" ", ""):
                best, match = 1.0, s
        for s in c.syn:
            if h == s:
                return 1.0, s
            if s in h:
                score = 0.6 + 0.35 * len(s) / len(h)
                if score > best:
                    best, match = score, s
    if c.buyer_sub:
        for prefix in BUYER_PREFIXES:
            if h.startswith(prefix) and len(h) > len(prefix):
                rest = h[len(prefix):]
                if rest in c.buyer_sub and 0.95 > best:
                    best, match = 0.95, prefix + rest
    return best, match


# ------------------------------------------------------------------ propose

@dataclass
class Candidate:
    score: float
    concept: str
    col: int
    reason: str


def _number_style(p: Profile, table_style: str) -> str:
    if p.de > p.en:
        return "de_decimal"
    if p.en > p.de:
        return "en_decimal"
    return table_style


def _date_transform(p: Profile) -> str:
    return "date_iso" if p.date_iso > p.date_dmy else "date_dmy"


def detect_grouping(table: Table, col: int | None) -> str:
    if col is None:
        return "row_per_invoice"
    seen: set[str] = set()
    blanks_after_first = 0
    for i, row in enumerate(table.rows):
        v = row[col].strip()
        if not v:
            if i > 0:
                blanks_after_first += 1
            continue
        if v in seen:
            return "row_per_line"
        seen.add(v)
    if blanks_after_first and blanks_after_first >= len(table.rows) // 4:
        return "row_per_line"
    return "row_per_invoice"


def _field(target: str, *, source_column: str | None = None, constant: str | None = None,
           transform: list[str] | None = None, confidence: float, reason_de: str) -> dict:
    f: dict = {"target": target}
    if source_column is not None:
        f["source_column"] = source_column
        f["transform"] = list(transform or [])
    else:
        f["constant"] = constant
    f["confidence"] = round(max(0.0, min(1.0, confidence)), 2)
    f["reason_de"] = reason_de
    return f


def propose_heuristic(table: Table, seller_profile: dict) -> dict:
    cols = table.columns
    columns_values = [[row[i] if i < len(row) else "" for row in table.rows] for i in range(len(cols))]
    profiles = [profile_column(v) for v in columns_values]
    de_total = sum(p.de for p in profiles)
    en_total = sum(p.en for p in profiles)
    if de_total > en_total:
        table_style = "de_decimal"
    elif en_total > de_total:
        table_style = "en_decimal"
    else:
        table_style = "en_decimal" if table.delimiter == "," else "de_decimal"

    cands: list[Candidate] = []
    for ci, header in enumerate(cols):
        p = profiles[ci]
        if p.iban >= 0.5:
            continue  # IBANs belong to the seller profile; never mapped
        for c in CONCEPTS:
            s, match = name_score(header, c)
            if s <= 0:
                continue
            ok = kind_ok(c.kind, p)
            if c.key == "vat_rate" and "%" in header:
                s = min(1.0, s + 0.1)
            score = s * (1.0 if ok else 0.15)
            if score < 0.45:
                continue
            reason = f"Spaltenname '{header}' passt zu '{c.label_de}'; {describe_profile(p)}"
            cands.append(Candidate(score, c.key, ci, reason))
        # value-only detection for unambiguous patterns
        if p.n and p.email >= 0.9:
            cands.append(Candidate(0.6, "buyer_email", ci, f"Spalte '{header}' enthält E-Mail-Adressen"))
        if p.n and p.vatid >= 0.8 and p.alpha >= 0.8:
            cands.append(Candidate(0.55, "buyer_vat_id", ci, f"Spalte '{header}' enthält USt-IdNr.-Muster"))

    cands.sort(key=lambda c: (-c.score, c.col))
    chosen: dict[str, Candidate] = {}
    used_cols: set[int] = set()
    for c in cands:
        if c.concept in chosen or c.col in used_cols:
            continue
        chosen[c.concept] = c
        used_cols.add(c.col)

    num_cand = chosen.get("number")
    num_col = num_cand.col if num_cand else None
    mode = detect_grouping(table, num_col)

    fields: list[dict] = []

    def add_col(target: str, cand: Candidate, transform: list[str]) -> None:
        fields.append(_field(target, source_column=cols[cand.col], transform=transform,
                             confidence=cand.score, reason_de=cand.reason))

    def num_transform(cand: Candidate, signed: bool = True) -> list[str]:
        p = profiles[cand.col]
        t = [_number_style(p, table_style)]
        if signed and p.negative:
            t.append("abs")
        return t

    for key, target in DIRECT_TARGETS.items():
        cand = chosen.get(key)
        if not cand:
            continue
        p = profiles[cand.col]
        concept = CONCEPT_BY_KEY[key]
        if concept.kind == "date":
            add_col(target, cand, [_date_transform(p)])
        elif key == "quantity":
            add_col(target, cand, num_transform(cand))
        elif key == "vat_rate":
            add_col(target, cand, [_number_style(p, table_style)])
            fields.append(_field("/lines/*/vat_category", source_column=cols[cand.col], transform=["rate_to_category"],
                                 confidence=cand.score * 0.95,
                                 reason_de=f"Steuerkategorie aus dem Steuersatz in '{cols[cand.col]}' (über 0 % = S)"))
        elif key == "unit":
            add_col(target, cand, ["unit_map"])
        elif key == "currency":
            add_col(target, cand, ["upper"])
        else:
            add_col(target, cand, [])
        if key == "buyer_email":
            fields.append(_field("/buyer/electronic_address_scheme", constant="EM", confidence=1.0,
                                 reason_de="Elektronische Adresse ist eine E-Mail (Schema EM)"))

    # ---- prices
    has_qty = "quantity" in chosen
    price = None
    if "unit_net" in chosen:
        c = chosen["unit_net"]
        price = _field("/lines/*/net_price", source_column=cols[c.col], transform=num_transform(c), confidence=c.score, reason_de=c.reason)
    elif "unit_gross" in chosen:
        c = chosen["unit_gross"]
        price = _field("/lines/*/net_price", source_column=cols[c.col], transform=num_transform(c) + ["gross_to_net"],
                       confidence=c.score * 0.9, reason_de=c.reason + "; Bruttopreis wird mit dem Steuersatz in netto umgerechnet")
    elif "line_net" in chosen and not has_qty:
        c = chosen["line_net"]
        price = _field("/lines/*/net_price", source_column=cols[c.col], transform=num_transform(c), confidence=c.score * 0.85,
                       reason_de=c.reason + "; kein Einzelpreis vorhanden, Betrag gilt bei Menge 1")
    elif "line_gross" in chosen and not has_qty:
        c = chosen["line_gross"]
        price = _field("/lines/*/net_price", source_column=cols[c.col], transform=num_transform(c) + ["gross_to_net"],
                       confidence=c.score * 0.75,
                       reason_de=c.reason + "; nur Bruttobetrag vorhanden, wird bei Menge 1 in netto umgerechnet")
    if price:
        fields.append(price)
    if not has_qty and price:
        fields.append(_field("/lines/*/quantity", constant="1", confidence=0.7,
                             reason_de="Keine Mengenspalte gefunden: eine Position je Rechnung mit Menge 1"))

    # ---- totals as booked in the source (only meaningful when one row is one invoice)
    if mode == "row_per_invoice":
        for key, target in (("line_net", "/source/expected_totals/net"), ("vat_amount", "/source/expected_totals/vat"),
                            ("line_gross", "/source/expected_totals/gross")):
            c = chosen.get(key)
            if c:
                fields.append(_field(target, source_column=cols[c.col], transform=num_transform(c), confidence=c.score * 0.9,
                                     reason_de=c.reason + "; dient als Kontrollsumme"))

    # ---- defaults / constants
    defaults = (seller_profile or {}).get("defaults", {}) or {}
    have = {f["target"] for f in fields}
    if "/lines/*/vat_rate" not in have:
        rate = str(defaults.get("vat_rate", "19"))
        fields.append(_field("/lines/*/vat_rate", constant=rate, confidence=0.6,
                             reason_de=f"Keine Steuersatz-Spalte gefunden: Standard aus dem Firmenprofil ({rate} %)"))
    if "/lines/*/vat_category" not in have:
        cat = str(defaults.get("vat_category", "S"))
        fields.append(_field("/lines/*/vat_category", constant=cat, confidence=0.6,
                             reason_de=f"Keine Steuersatz-Spalte gefunden: Steuerkategorie aus dem Firmenprofil ({cat})"))
    if "/lines/*/unit" not in have:
        qcol = chosen.get("quantity")
        qname = compact(cols[qcol.col]) if qcol else ""
        if qname in ("stunden", "std", "hours"):
            fields.append(_field("/lines/*/unit", constant="HUR", confidence=0.8, reason_de="Mengenspalte zählt Stunden: Einheit HUR"))
        elif qname in ("tage", "days"):
            fields.append(_field("/lines/*/unit", constant="DAY", confidence=0.8, reason_de="Mengenspalte zählt Tage: Einheit DAY"))
        else:
            unit = str(defaults.get("unit", "C62"))
            fields.append(_field("/lines/*/unit", constant=unit, confidence=0.6,
                                 reason_de=f"Keine Einheiten-Spalte gefunden: Standard aus dem Firmenprofil ({unit})"))
    if "/buyer/country" not in have:
        fields.append(_field("/buyer/country", constant="DE", confidence=0.6,
                             reason_de="Keine Länderspalte gefunden: Deutschland angenommen"))
    if "/lines/*/description" not in have:
        fields.append(_field("/lines/*/description", constant="Leistung", confidence=0.3,
                             reason_de="Keine Beschreibungsspalte gefunden: Platzhalter 'Leistung' – bitte prüfen"))
    # /buyer_reference stays unmapped when no column exists: the app asks the user.

    return {
        "mapping_id": str(uuid.uuid4()),
        "version": 1,
        "provider": "heuristic",
        "grouping": {"mode": mode, "invoice_number_column": cols[num_col] if num_col is not None else None},
        "fields": fields,
    }
