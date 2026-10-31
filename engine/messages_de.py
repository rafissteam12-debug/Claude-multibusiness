"""German explanations for the most common rule IDs.

Every ID below exists in the pinned rule files in engine/rules/ (checked by
engine/tests/test_engine_messages.py). Unknown IDs get a German frame around the
original rule text (`fallback`). The original text is always kept as `text_en`.
"""
from __future__ import annotations

MESSAGES_DE: dict[str, str] = {
    # XRechnung (KoSIT, engine/rules/xrechnung)
    "BR-DE-1": "Zahlungsangaben (BG-16) fehlen. Bitte Zahlungsart und Bankverbindung angeben.",
    "BR-DE-2": "Kontaktdaten des Verkäufers (BG-6) fehlen: Name, Telefon und E-Mail einer Ansprechperson.",
    "BR-DE-3": "Ort des Verkäufers (BT-37) fehlt.",
    "BR-DE-4": "Postleitzahl des Verkäufers (BT-38) fehlt.",
    "BR-DE-5": "Name der Ansprechperson des Verkäufers (BT-41) fehlt.",
    "BR-DE-6": "Telefonnummer der Ansprechperson des Verkäufers (BT-42) fehlt.",
    "BR-DE-7": "E-Mail-Adresse der Ansprechperson des Verkäufers (BT-43) fehlt.",
    "BR-DE-15": "Käuferreferenz bzw. Leitweg-ID (BT-10) fehlt. Für XRechnung ist sie Pflicht; "
                "öffentliche Auftraggeber nennen ihre Leitweg-ID im Auftrag.",
    "BR-DE-16": "Steuerangabe des Verkäufers fehlt: USt-IdNr. (BT-31), Steuernummer (BT-32) "
                "oder Steuervertreter (BG-11) angeben.",
    "BR-DE-19": "Die IBAN (BT-84) ist formal nicht korrekt (Länge oder Prüfziffer).",
    "BR-DE-23-a": "Bei Überweisung (Code 30 oder 58) muss eine Bankverbindung (BG-17) angegeben sein.",
    "BR-DE-21": "Die Spezifikationskennung (BT-24) entspricht nicht der Kennung für XRechnung.",
    # EN 16931 (CEN, engine/rules/cen)
    "BR-16": "Die Rechnung enthält keine Rechnungsposition (BG-25).",
    "BR-62": "Bei der elektronischen Adresse des Verkäufers (BT-34) fehlt das Schema (z. B. EM für E-Mail).",
    "BR-63": "Bei der elektronischen Adresse des Käufers (BT-49) fehlt das Schema (z. B. EM für E-Mail).",
    "BR-CO-10": "Die Summe der Positionsbeträge (BT-106) stimmt nicht mit den einzelnen Positionen (BT-131) überein.",
    "BR-CO-13": "Der Gesamtbetrag netto (BT-109) stimmt nicht: Summe der Positionen minus Nachlässe plus Zuschläge.",
    "BR-CO-15": "Der Bruttobetrag (BT-112) ist nicht gleich Nettobetrag (BT-109) plus Umsatzsteuer (BT-110).",
    "BR-CO-16": "Der Zahlbetrag (BT-115) ist nicht gleich Bruttobetrag minus Anzahlung plus Rundung.",
    "BR-CO-17": "Der Steuerbetrag einer USt-Gruppe (BT-117) ist nicht Bemessungsgrundlage mal Steuersatz (gerundet).",
    "BR-CO-25": "Bei positivem Zahlbetrag muss ein Fälligkeitsdatum (BT-9) oder Zahlungsbedingungen (BT-20) angegeben sein.",
    "BR-CO-26": "Der Verkäufer braucht eine Kennung: Verkäufer-ID (BT-29), Handelsregisternummer (BT-30) "
                "oder USt-IdNr. (BT-31).",
    "BR-S-08": "Bei Normalsatz (S) stimmt die Bemessungsgrundlage einer USt-Gruppe nicht mit den zugehörigen Positionen überein.",
    "BR-E-10": "Bei steuerbefreiten Umsätzen (Kategorie E) fehlt der Befreiungsgrund (BT-120 Text oder BT-121 Code).",
    "BR-Z-10": "Bei Nullsatz (Kategorie Z) darf kein Befreiungsgrund angegeben werden.",
    "BR-AE-10": "Bei Steuerschuldnerschaft des Leistungsempfängers (AE) fehlt der Hinweis (BT-120 oder BT-121, z. B. VATEX-EU-AE).",
    "BR-O-02": "Bei „nicht steuerbar“ (Kategorie O) darf keine USt-IdNr. des Verkäufers, des Käufers "
               "oder eines Steuervertreters angegeben sein.",
    "BR-O-10": "Bei „nicht steuerbar“ (Kategorie O) fehlt der Befreiungsgrund (BT-120 oder BT-121, z. B. VATEX-EU-O).",
    "BR-50": "Bei Überweisung fehlt die Kontonummer bzw. IBAN des Zahlungsempfängers (BT-84).",
    "BR-61": "Bei Überweisung (Code 30 oder 58) muss die IBAN bzw. Kontokennung (BT-84) angegeben sein.",
}

# Engine-side input/format problems (not from rule files).
ENGINE_MESSAGES_DE: dict[str, str] = {
    "FILE-TOO-LARGE": "Die Datei ist größer als 5 MB und wird nicht geprüft.",
    "FILE-EMPTY": "Die Datei ist leer.",
    "XML-NOT-WELLFORMED": "Die Datei ist kein gültiges XML (nicht wohlgeformt).",
    "XML-DOCTYPE": "Die XML-Datei enthält eine DOCTYPE-Deklaration. Aus Sicherheitsgründen werden solche Dateien "
                   "nicht verarbeitet; E-Rechnungen brauchen keine DOCTYPE-Angabe.",
    "PDF-NO-XML": "Im PDF ist keine strukturierte Rechnung (ZUGFeRD/Factur-X-XML) eingebettet. "
                  "Ein reines PDF ist keine E-Rechnung.",
    "PDF-UNREADABLE": "Das PDF konnte nicht gelesen werden.",
    "FORMAT-UNKNOWN": "Unbekanntes Format: weder UN/CEFACT CII noch UBL.",
}


def message_for(rule_id: str | None, original: str) -> str:
    if rule_id and rule_id in MESSAGES_DE:
        return MESSAGES_DE[rule_id]
    if rule_id and rule_id in ENGINE_MESSAGES_DE:
        return ENGINE_MESSAGES_DE[rule_id]
    return f"Regel {rule_id or 'unbekannt'} nicht erfüllt. Originaltext: {original}"
