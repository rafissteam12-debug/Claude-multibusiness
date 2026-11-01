---
title: "Datenschutz-Fakten (Checkliste für die Datenschutzhinweise)"
status: "Faktensammlung, kein Rechtstext. Rechtsgrundlagen, Fristen-Begründungen und Bewertungen ergänzt die rechtliche Prüfung."
last_checked: "2026-11-01"
code_state: "agent/content auf main c987f2f"
---

# Datenschutz-Fakten

Diese Liste beschreibt, **welche Daten Website und Anwendung tatsächlich verarbeiten**, abgeleitet aus dem Code
(`app/migrations/001_init.sql`, `app/main.py`, `app/jobs.py`, `app/security.py`, `app/mailer.py`, `mapping/ai.py`,
`ops/Caddyfile`, `ops/docker-compose.yml`, `site/static/site.js`) und den Verträgen in `contracts/`.
Sie ist die Vorlage für die Datenschutzhinweise der Website. Sie enthält **keine rechtlichen Schlussfolgerungen**.

Spalte „Stand“: **ist** = so im Code; **geplant** = beschlossen (Review wave 4), im Code noch nicht umgesetzt.

## Verantwortlicher

`[[BUSINESS_ID_PENDING]]` (Name, Anschrift, Kontakt des Verantwortlichen; ggf. Datenschutzkontakt).

## Website (statisch)

| Daten | Zweck | Wo | Speicherdauer | Stand |
| --- | --- | --- | --- | --- |
| Verbindungsdaten beim Seitenabruf (u. a. IP-Adresse, Browserangaben) | Auslieferung der Seiten | Cloudflare (Auslieferung der statischen Website) | nach den Bedingungen von Cloudflare | ist |
| Cookies, lokale Speicherung im Browser | – | – | keine; die Website setzt keine Cookies | ist |
| Schriften, Skripte, Grafiken von Dritten | – | – | keine; alles vom eigenen Server | ist |
| Ereignismeldungen (`page_view`, `link_click`, `check_run`, `subscribe`): Ereignisname, Pfad, ggf. Kampagnenkürzel (z. B. `ig-001`), Zeitpunkt | Nutzungszählung | Tabelle `events` der Anwendung | ohne Frist (keine Löschregel im Code) | ist; Löschung/Aggregation nach z. B. 13 Monaten geplant (Review L4) |
| IP-Adresse bei Ereignismeldungen | Begrenzung auf 600 Meldungen pro Stunde | nur als gesalzener Hashwert in `rate_hits` | 2 Tage | ist |

Die Tabelle `events` enthält **keine** IP-Adresse, keine Gerätekennung, keine Nutzerkennung.

## Kostenloser E-Rechnung-Check

| Daten | Zweck | Speicherdauer | Stand |
| --- | --- | --- | --- |
| Hochgeladene XML- oder PDF-Datei (bis 5 MB; kann personenbezogene Daten enthalten) | Prüfung | nicht gespeichert; nach der Antwort verworfen | ist |
| Prüfbericht | Anzeige im Browser | nicht gespeichert | ist |
| IP-Adresse | Begrenzung auf 20 Prüfungen pro Stunde | nur als gesalzener Hashwert in `rate_hits`, 2 Tage | ist |

## Anwendung Belegbrücke

### Konto und Anmeldung

| Daten | Tabelle | Speicherdauer | Stand |
| --- | --- | --- | --- |
| Login-E-Mail-Adresse, Plan, Zeitpunkt der Kontoerstellung, Zeitpunkt der letzten Anmeldung | `users` | solange das Konto besteht | ist |
| Löschung auf Wunsch („Konto löschen“ im Profil, sofort) und nach 12 Monaten ohne Anmeldung | – | – | geplant (Review H4) |
| Sitzung: Hashwert der Sitzungskennung, CSRF-Token, Erstellungs- und Ablaufzeit; Sitzungs-Cookie (HttpOnly) | `sessions` | bis Ablauf (7 Tage), dann gelöscht | ist |
| Anmelde-, Bestätigungs- und Abmeldelinks: nur HMAC-Hashwert des Tokens, Zweck, E-Mail-Adresse, Zeitpunkte | `tokens` | Anmelde-/Bestätigungslink 15 Minuten gültig, Abmeldelink 1 Jahr; gelöscht 1 Stunde nach Ablauf | ist |
| Kurzlebiges Cookie `bb_pre` vor der Anmeldung (CSRF-Schutz) | Browser | 1 Stunde | ist |
| Begrenzung von Anmeldelinks: Hashwert der E-Mail-Adresse (5 pro Stunde) und der IP-Adresse (20 pro Stunde) | `rate_hits` | 2 Tage | ist |

### Unternehmensprofil (Verkäuferdaten)

Tabelle `seller_profiles`, ein Profil je Konto, solange das Konto besteht. Inhalt (aus `app/profile.py`):
Firmenname, Straße, PLZ, Ort, Land; USt-IdNr., Steuernummer, Registernummer, Verkäuferkennung (BT-29) mit Schema;
elektronische Adresse und deren Art; Ansprechpartner (Name, Telefon, E-Mail); Zahlungsangaben (Zahlungsart, **IBAN**, BIC,
Kontoinhaber, Zahlungsziel, Zahlungsbedingungen); Standardwerte (Steuerkategorie, Steuersatz, Einheit, Format, Befreiungsgründe).
Der Ansprechpartner kann eine natürliche Person sein. Export als JSON („Daten exportieren“): **geplant** (Review H4).

### Hochgeladene Exporte (CSV/XLSX)

| Daten | Tabelle/Ort | Speicherdauer | Stand |
| --- | --- | --- | --- |
| Rohdatei (bis 10 MB; enthält Rechnungs- und Kundendaten) | `TEMP_DIR/uploads` | gelöscht nach abgeschlossener Umwandlung, spätestens nach 24 Stunden | ist |
| Dateiname | `uploads.filename` | zusammen mit der Rohdatei gelöscht | ist |
| Metadaten: Dateityp, Größe, Zeilenzahl, **Spaltennamen**, Zeitpunkte | `uploads` | ohne Frist (bleiben nach Löschung der Datei) | ist; Löschung mit der Datei (nur Zähler bleiben) geplant (Review M12) |
| Begrenzung auf 60 Uploads pro Stunde: Nutzerkennung als Schlüssel | `rate_hits` | 2 Tage | ist |

Hinweis zur Umsetzung: Nach Review M7 soll die Rohdatei nur nach einer Umwandlung mit mindestens einer gültigen Datei sofort gelöscht werden, sonst nach 24 Stunden.

### Zuordnungen (Mappings)

Tabelle `mappings`: Spaltennamen, Zuordnung Spalte → Rechnungsfeld, Umwandlungen, **vom Nutzer eingetragene feste Werte**
(z. B. eine feste Käuferreferenz), Konfidenz und Begründung, verwendeter Anbieter (`heuristic` oder `anthropic`) und Modellname,
Zeitpunkte. **Keine Zellinhalte aus der Datei.** Speicherdauer: solange das Konto besteht (kein eigener Löschknopf; Löschung mit dem Konto).

### Umwandlungsaufträge, erzeugte Dateien, Fehlertexte

| Daten | Tabelle/Ort | Speicherdauer | Stand |
| --- | --- | --- | --- |
| Erzeugte Dateien: XRechnung (XML), ZUGFeRD (PDF), lesbares PDF („keine E-Rechnung“), ZIP | `TEMP_DIR/outputs`, Tabelle `files` | Dateien und Dateinamen nach 24 Stunden gelöscht; Zeile mit Art, Medientyp, Zeitpunkten bleibt | ist |
| Ergebnisse je Rechnung und Fehlertexte (können Zellinhalte enthalten, z. B. Rechnungsnummern) | `jobs.result_json`, `jobs.error_de` | nach 24 Stunden geleert (Status „abgelaufen“) | ist |
| Auftragsdaten ohne Inhalte: Formate, Profil, Status, Anzahl Rechnungen, Anzahl gültiger Rechnungen, Zeitpunkte | `jobs` | solange das Konto besteht | ist |
| Freigegebene Speicherseiten der Datenbank können gelöschte Texte noch enthalten | SQLite-Datei | bis überschrieben | ist; `secure_delete` geplant (Review L9) |

### Nutzungszähler

Tabelle `usage`: Nutzerkennung, Monat (deutsche Zeit), Anzahl gültiger Rechnungen. Speicherdauer: solange das Konto besteht.

### Protokolle

- Anwendung: keine Rechnungsinhalte, keine KI-Anfragen mit Werten, keine Tokens; Fehler nur mit Name der Fehlerklasse.
- Webserver (Caddy, Zugriffsprotokoll): IP-Adressen gekürzt (IPv4 auf /16, IPv6 auf /32), Token aus der Adresse entfernt,
  Cookies, Authorization, CSRF-Token und `X-Forwarded-For` nicht protokolliert; keine Inhalte. Rotation nach Größe
  (10 MB × 5 Dateien), keine Frist in Tagen. Offen: `Referer` kann Tokens enthalten (Review M2, Korrektur geplant).

## E-Mail-Hinweise (Double-Opt-in)

| Daten | Tabelle | Speicherdauer | Stand |
| --- | --- | --- | --- |
| E-Mail-Adresse, Version des Einwilligungstextes (`2026-10-31-v1`), Quelle der Anmeldung (`check`, `guide`, `ig-…`), Zeitpunkt der Anfrage, der Bestätigung, des Versands der zweiten Willkommens-E-Mail | `subscribers` | bis zur Abmeldung | ist |
| Nicht bestätigte Anfragen | `subscribers` | **7 Tage**, dann gelöscht (`app/jobs.py`, `purge`) | ist |
| Abmeldung | – | Adresse und Einwilligungsdatensatz werden sofort gelöscht | ist; minimaler Nachweis (Hashwert, Version, Daten) geplant (Review L4) |
| Begrenzung: Hashwert der IP (10 pro Stunde) und der E-Mail-Adresse (3 pro Stunde) | `rate_hits` | 2 Tage | ist |

Umfang der Einwilligung v1 (`contracts/api.md`): Willkommens-E-Mails und gelegentliche Hinweise zu Regeländerungen der E-Rechnung
und zu Belegbrücke. Die Adresse wird nicht verkauft und nur für diese E-Mails genutzt.

## Dienstleister

| Dienstleister | Wofür | Welche Daten | Wann | Hinweis |
| --- | --- | --- | --- | --- |
| **Brevo** (E-Mail-Versand) | Anmeldelinks, Bestätigungs-E-Mail, Willkommens-E-Mails | Empfängeradresse, Betreff und Text der E-Mail (mit Link) | nur wenn `MAILER=brevo` gesetzt ist | Auftragsverarbeitung: Vertrag (AVV/DPA) mit Brevo abschließen |
| **Anthropic** (KI-Modell für den Zuordnungsvorschlag) | Vorschlag der Spaltenzuordnung | Spaltennamen, Form der Werte aus bis zu 5 Beispielzeilen („31.10.2026“ → „dd.dd.dddd“), statistische Spaltenhinweise (z. B. „enthält negative Werte“), Zeilenzahl, Standard-Steuersatz, -Steuerkategorie und -Einheit aus dem Profil; **echte Werte nur**, wenn der Nutzer „Echte Beispielwerte an die KI senden“ einschaltet | nur wenn `AI_PROVIDER=anthropic` gesetzt ist | Anthropic ist ein Unternehmen mit Sitz in den USA (Vertragspartner und Sitz aus dem Vertrag übernehmen); Daten können also in ein Drittland übermittelt werden. Bewertung und Grundlage (z. B. Vertrag, Angemessenheitsbeschluss) durch die rechtliche Prüfung |
| **Cloudflare** (Auslieferung der statischen Website) | Seitenauslieferung | Verbindungsdaten der Besucher (u. a. IP-Adresse) | immer für die Website | Cloudflare ist ein Unternehmen mit Sitz in den USA (Vertragspartner und Sitz aus dem Vertrag übernehmen); Bewertung durch die rechtliche Prüfung. Die Anwendung selbst läuft nicht über Cloudflare (DNS ohne Proxy, Review L8) |
| **Server-Hosting der Anwendung** | Betrieb von Anwendung, Datenbank, temporären Dateien | alle oben unter „Anwendung“ genannten Daten | immer | geplant: VPS in der EU (`ops/RUNBOOK.md`); Anbieter `[[BUSINESS_ID_PENDING]]` |

Ohne diese Einstellungen (Standard) verlässt bei der Zuordnung nichts den Server (heuristischer Vorschlag), und E-Mails werden
nur in der Konsole ausgegeben (nur Entwicklung).

## Für die Datenschutzhinweise noch zu klären (Inhaber / rechtliche Prüfung)

- Verantwortlicher und Kontakt: `[[BUSINESS_ID_PENDING]]`.
- Rechtsgrundlagen je Verarbeitung.
- Verträge zur Auftragsverarbeitung mit Brevo, Anthropic, Cloudflare und dem Hoster; Angaben zur Drittlandübermittlung.
- Sitz und Vertragspartner der Dienstleister aus den Verträgen übernehmen (beim Schreiben dieser Liste waren deren Rechtsseiten
  aus der Arbeitsumgebung nicht abrufbar).
