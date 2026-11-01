---
title: "Datenschutz-Fakten (Checkliste für die Datenschutzhinweise)"
status: "Faktensammlung, kein Rechtstext. Rechtsgrundlagen, Fristen-Begründungen und Bewertungen ergänzt die rechtliche Prüfung."
last_checked: "2026-11-01"
code_state: "main 9eb2720 (Remediation-Release)"
---

# Datenschutz-Fakten

Diese Liste beschreibt, **welche Daten Website und Anwendung tatsächlich verarbeiten**, abgeleitet aus dem Code
(`app/migrations/001_init.sql`, `app/main.py`, `app/jobs.py`, `app/security.py`, `app/mailer.py`, `mapping/ai.py`,
`app/migrations/003_*.sql`, `ops/Caddyfile`, `ops/docker-compose.yml`, `site/static/site.js`) und den Verträgen in `contracts/`.
Sie ist die Vorlage für die Datenschutzhinweise der Website. Sie enthält **keine rechtlichen Schlussfolgerungen**.

Spalte „Stand“: **ist** = so im Code; **geplant** = beschlossen, im Code noch nicht umgesetzt. Stand nach Merge der wave-4-Korrekturen; alle Punkte unten im Code nachgeprüft.

## Verantwortlicher

`[[BUSINESS_ID_PENDING]]` (Name, Anschrift, Kontakt des Verantwortlichen; ggf. Datenschutzkontakt).

## Website (statisch)

| Daten | Zweck | Wo | Speicherdauer | Stand |
| --- | --- | --- | --- | --- |
| Verbindungsdaten beim Seitenabruf (u. a. IP-Adresse, Browserangaben) | Auslieferung der Seiten | Cloudflare (Auslieferung der statischen Website) | nach den Bedingungen von Cloudflare (Frist aus der Cloudflare-Dokumentation übernehmen, offen) | ist |
| Cookies, lokale Speicherung im Browser | – | – | keine; die Website setzt keine Cookies | ist |
| Schriften, Skripte, Grafiken von Dritten | – | – | keine; alles vom eigenen Server | ist |
| Ereignismeldungen (`page_view`, `link_click`, `check_run`, `subscribe`): Ereignisname, Pfad, ggf. Kampagnenkürzel (z. B. `ig-001`), Zeitpunkt | Nutzungszählung | Tabelle `events` der Anwendung | etwa 13 Monate (396 Tage), dann gelöscht | ist |
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
| Löschung auf Wunsch: Knopf „Konto löschen“ im Profil (`DELETE /api/v1/account`), sofort: Konto, Sitzungen, Login-Tokens, Unternehmensprofil, Zuordnungen, Uploads, erzeugte Dateien, Aufträge, Nutzungszähler, zugehörige Rate-Limit-Einträge | alle | sofort | ist |
| Konten ohne Anmeldung seit 12 Monaten (365 Tage) | alle | automatisch mit allen Daten wie oben gelöscht | ist |
| Sitzung: Hashwert der Sitzungskennung, CSRF-Token, Erstellungs- und Ablaufzeit; Sitzungs-Cookie (HttpOnly) | `sessions` | bis Ablauf (7 Tage), dann gelöscht | ist |
| Anmelde-, Bestätigungs- und Abmeldelinks: nur HMAC-Hashwert des Tokens, Zweck, E-Mail-Adresse, Zeitpunkte | `tokens` | Anmelde-/Bestätigungslink 15 Minuten gültig, Abmeldelink 1 Jahr; gelöscht 1 Stunde nach Ablauf | ist |
| Kurzlebiges Cookie `bb_pre` vor der Anmeldung (CSRF-Schutz) | Browser | 1 Stunde | ist |
| Kurzlebiges HttpOnly-Cookie mit dem Token eines Anmelde-, Bestätigungs- oder Abmeldelinks | Browser | 15 Minuten (Anmeldung, Bestätigung), 1 Stunde (Abmeldung) | ist |
| Annahme der AGB: Versionskennung (heute `agb-draft-1`, nächste `agb-draft-2`), Zeitpunkt der Annahme, Zeitpunkt der B2B-Bestätigung; im Datenexport enthalten | `users` (`terms_version`, `terms_accepted_at`, `b2b_confirmed_at`) | solange das Konto besteht | ist |
| Annahme des AVV: Versionskennung `avv-draft-1`, Zeitpunkt, Konto; im Datenexport enthalten | `users` (App in Arbeit) | solange das Konto besteht | geplant |
| Begrenzung von Anmeldelinks: Hashwert der E-Mail-Adresse (5 pro Stunde) und der IP-Adresse (20 pro Stunde) | `rate_hits` | 2 Tage | ist |

### Unternehmensprofil (Verkäuferdaten)

Tabelle `seller_profiles`, ein Profil je Konto, solange das Konto besteht. Inhalt (aus `app/profile.py`):
Firmenname, Straße, PLZ, Ort, Land; USt-IdNr., Steuernummer, Registernummer, Verkäuferkennung (BT-29) mit Schema;
elektronische Adresse und deren Art; Ansprechpartner (Name, Telefon, E-Mail); Zahlungsangaben (Zahlungsart, **IBAN**, BIC,
Kontoinhaber, Zahlungsziel, Zahlungsbedingungen); Standardwerte (Steuerkategorie, Steuersatz, Einheit, Format, Befreiungsgründe).
Der Ansprechpartner kann eine natürliche Person sein. Export als JSON: Knopf „Daten herunterladen (JSON)“ im Profil (`GET /api/v1/account/export`) mit Konto (E-Mail, Plan, Zeitpunkte), Unternehmensprofil, gespeicherten Zuordnungen und Nutzungszählern: **ist**.

### Hochgeladene Exporte (CSV/XLSX)

| Daten | Tabelle/Ort | Speicherdauer | Stand |
| --- | --- | --- | --- |
| Rohdatei (bis 10 MB; enthält Rechnungs- und Kundendaten) | `TEMP_DIR/uploads` | gelöscht nach erfolgreicher Umwandlung, spätestens nach 24 Stunden | ist |
| Dateiname | `uploads.filename` | zusammen mit der Rohdatei gelöscht | ist |
| Beispielwerte: erster nicht leerer Wert je Spalte (höchstens 60 Zeichen) für die Zuordnungsseite | `uploads.samples_json` | zusammen mit der Rohdatei gelöscht | ist |
| Metadaten: Spaltennamen, Größe | `uploads` | zusammen mit der Rohdatei gelöscht | ist |
| Dateityp, Zeilenzahl, Zeitpunkte | `uploads` | solange das Konto besteht (Statistik) | ist |
| Begrenzung auf 60 Uploads pro Stunde: Nutzerkennung als Schlüssel | `rate_hits` | 2 Tage | ist |

Sofort gelöscht wird die Rohdatei nur nach einer erfolgreichen Umwandlung (mindestens eine gültige Datei angeboten); sonst bleibt sie bis 24 Stunden, damit die Zuordnung korrigiert werden kann (`app/jobs.py`).

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
| Freigegebene Speicherseiten der Datenbank können gelöschte Texte noch enthalten | SQLite-Datei | nicht mehr: `PRAGMA secure_delete = ON` überschreibt gelöschte Inhalte (`app/db.py`) | ist |

### Nutzungszähler

Tabelle `usage`: Nutzerkennung, Monat (deutsche Zeit), Anzahl gültiger Rechnungen. Speicherdauer: solange das Konto besteht.

### Protokolle

- Anwendung: keine Rechnungsinhalte, keine KI-Anfragen mit Werten, keine Tokens; Fehler nur mit Name der Fehlerklasse.
- Webserver (Caddy, Zugriffsprotokoll): IP-Adressen gekürzt (IPv4 auf /16, IPv6 auf /32), Token aus der Adresse entfernt,
  Cookies, Authorization, CSRF-Token und `X-Forwarded-For` nicht protokolliert; keine Inhalte. Entscheidung des Inhabers:
  Server- und Container-Protokolle **14 Tage**. Stand: **ist (nur größenbasierte Rotation)** – Caddy-Zugriffsprotokoll `roll_keep_for 336h`
  (rotierte Dateien älter als 14 Tage werden gelöscht; die aktive Datei kann bei wenig Verkehr älter sein), Container-Protokolle
  `json-file` 5 MB × 3 Dateien. Strenge tägliche Rotation mit Löschung nach 14 Tagen und journald-Grenzen
  (`MaxRetentionSec=14day`): **geplant – wird mit Servereinrichtung aktiv** (Ops-Agent in Arbeit; erst nach Merge und
  Einrichtung auf dem Server als „ist“ angeben). **Keine Backups** (`ops/RUNBOOK.md`: Kundendaten leben höchstens 24 Stunden). Der `Referer`-Header wird nicht protokolliert. Anmelde- und Bestätigungslinks: Der Token wird beim Aufruf in ein kurzlebiges HttpOnly-Cookie übernommen und die Seite ohne Token in der Adresse neu geladen (Weiterleitung mit `Referrer-Policy: no-referrer`).

## E-Mail-Hinweise (Double-Opt-in)

| Daten | Tabelle | Speicherdauer | Stand |
| --- | --- | --- | --- |
| E-Mail-Adresse, Version des Einwilligungstextes (`2026-10-31-v1`), Quelle der Anmeldung (`check`, `guide`, `ig-…`), Zeitpunkt der Anfrage, der Bestätigung, des Versands der zweiten Willkommens-E-Mail | `subscribers` | bis zur Abmeldung | ist |
| Nicht bestätigte Anfragen | `subscribers` | **7 Tage**, dann gelöscht (`app/jobs.py`, `purge`) | ist |
| Abmeldung | `subscribers` | Adresse sofort gelöscht | ist |
| Einwilligungsnachweis, bei jeder Bestätigung ein neuer Datensatz: HMAC der E-Mail-Adresse (keine Adresse), Einwilligungsversion, Quelle/Formular (`check`, `guide`, `ig-…`), Zeitpunkte von Anfrage und Bestätigung | `consent_records` | drei Fälle: (1) während die Anmeldung besteht: aufbewahrt; (2) nach Abmeldung: 3 Jahre nach der Abmeldung gelöscht; (3) Anmeldung entfällt ohne Abmeldung: 3 Jahre nach der Bestätigung gelöscht | ist |
| Widerrufsnachweis: Datum und Art der Abmeldung (`link`) | `consent_records.unsubscribed_at`, `.method` | wie oben | ist |
| Sperrwirkung: eine erneute Anmeldung braucht immer ein neues Double-Opt-in und erzeugt einen neuen Datensatz; frühere Abmeldungen werden nie ohne Bestätigung reaktiviert | `consent_records`, `subscribers` | wie oben | ist |
| Nicht gespeichert im Nachweis: E-Mail-Adresse im Klartext, IP-Adresse, Browserkennung | – | – | ist |

Der HMAC ist ein **pseudonymisierter Prüfwert**, keine Anonymisierung: Mit dem Schlüssel lässt sich prüfen, ob eine bestimmte
Adresse eingewilligt hatte; er bleibt personenbezogen (PRE_REVIEW 2.14, Q9). Schlüssel heute `SESSION_SECRET`; ein eigener
`CONSENT_HMAC_KEY` ist angefragt (**geplant**), damit ein Wechsel des Sitzungsschlüssels die Nachweise nicht unbrauchbar macht.
Wortlaut des Einwilligungstextes v1 als versionierte Datei: **geplant** (PRE_REVIEW 6.4, Orchestrator).
| Begrenzung: Hashwert der IP (10 pro Stunde) und der E-Mail-Adresse (3 pro Stunde) | `rate_hits` | 2 Tage | ist |

Begründung der 3-Jahres-Frist (Entscheidung des Inhabers, als Fakten, keine rechtliche Bewertung):
Nachweis der Einwilligung, Art. 7 Abs. 1 DSGVO (https://eur-lex.europa.eu/eli/reg/2016/679/oj);
regelmäßige Verjährungsfrist 3 Jahre, § 195 BGB (https://www.gesetze-im-internet.de/bgb/__195.html: „Die regelmäßige Verjährungsfrist beträgt drei Jahre.“ –
vom Orchestrator geöffnet und bestätigt, 1. Nov. 2026). **Begründung durch Fachberatung bestätigen.**

Umfang der Einwilligung v1 (`contracts/api.md`): Willkommens-E-Mails und gelegentliche Hinweise zu Regeländerungen der E-Rechnung
und zu Belegbrücke. Die Adresse wird nicht verkauft und nur für diese E-Mails genutzt.

## Dienstleister

| Dienstleister | Wofür | Welche Daten | Wann | Ort / Drittland (Fakten) | AVV/DPA |
| --- | --- | --- | --- | --- | --- |
| **Brevo** (E-Mail-Versand) | Anmeldelinks, Bestätigungs-E-Mail, Willkommens-E-Mails | Empfängeradresse, Betreff und Text der E-Mail (mit Link) | nur wenn `MAILER=brevo` gesetzt ist | Sitz, Hosting-Ort und Speicherdauer bei Brevo aus dem Vertrag übernehmen (nicht geprüft) | **offen** – vom Inhaber grundsätzlich angenommen (1. Nov. 2026); DPA steht in Brevos General Conditions of Use (Abschnitt am Ende; https://help.brevo.com/hc/en-us/articles/15403782599570); wirksam erst mit dem Brevo-Konto (eigene Freigabe) |
| **Anthropic** (KI-Modell für den Zuordnungsvorschlag) | Vorschlag der Spaltenzuordnung | Spaltennamen und Form der Werte aus bis zu 5 Beispielzeilen („31.10.2026“ → „dd.dd.dddd“), statistische Spaltenhinweise (z. B. „enthält negative Werte“), Zeilenzahl, Standard-Steuersatz, -Steuerkategorie und -Einheit aus dem Profil; **echte Werte nur**, wenn der Nutzer „Echte Beispielwerte an die KI senden“ einschaltet | nur wenn `AI_PROVIDER=anthropic` gesetzt ist; **Standard: aus** (heuristischer Vorschlag ohne Netzwerk). In Test- und Live-Betrieb (`APP_ENV=staging`/`prod`) erst nach rechtlicher Freigabe der Übermittlung einschaltbar: Schutz `AI_TRANSFER_CLEARED` – **geplant** (App-Agent in Arbeit; bis zum Merge nicht im Code) | Laut Anthropic-Dokumentation (am 1. Nov. 2026 geöffnet): Verarbeitung („inference geo“) standardmäßig `global` – „may run in any available geography“; einzige Alternative `us`; Speicherort des Workspace derzeit nur `us`; keine EU-Option dokumentiert; ein Workspace kann mit `default_inference_geo` einen anderen Standard setzen (https://platform.claude.com/docs/en/manage-claude/data-residency). **Konfiguration im Code (`mapping/ai.py`): `inference_geo` wird nicht gesetzt** → es gilt der Workspace-Standard, ohne Änderung `global`. **Workspace-Einstellungen (Datenstandort, `default_inference_geo`) sind hier nicht einsehbar – Aufgabe des Inhabers: in der Anthropic Console ablesen und mit Datum festhalten.** Keine Einstellung wird hier als gesetzt behauptet. Damit Übermittlung in ein Drittland (USA bzw. beliebige Region). Vertragspartner für Kunden im EWR laut Commercial Terms: Anthropic Ireland, Limited; Verarbeitung auch durch Anthropic PBC (USA) und Unterauftragsverarbeiter (https://www.anthropic.com/subprocessors). DPA: Standardvertragsklauseln Modul 2/3 (Beschluss 2021/914), DPF nicht genannt; Löschung binnen 30 Tagen nach Vertragsende; Speicherdauer bei API-Nutzung nicht geprüft (Quellen: https://www.anthropic.com/legal/commercial-terms, https://www.anthropic.com/legal/data-processing-addendum – vom Orchestrator geöffnet, `docs/legal/PRE_REVIEW.md`). Ob im Standardmodus (nur Wertformen) überhaupt personenbezogene Daten übermittelt werden: offene Frage Q3. Rechtsgrundlage/Garantien **prüfen** | **vom Inhaber angenommen** (1. Nov. 2026): DPA über die Commercial Terms (Abschnitt C); Übermittlungsgrundlage durch die Prüfung bestätigen |
| **Cloudflare** (Auslieferung der statischen Website) | Seitenauslieferung | Verbindungsdaten der Besucher (u. a. IP-Adresse) | immer für die Website | Sitz USA vom Inhaber anhand des Vertrags bestätigen. Customer DPA: **Version 6.4, „effective April 3, 2026“** – so am **1. Nov. 2026** auf https://www.cloudflare.com/cloudflare-customer-dpa/ angezeigt (vom Content-Agenten selbst geöffnet; ein separates Aktualisierungsdatum zeigt die Seite nicht). Als frühere Fassung listet die Seite nur „Version (2025-06-20)“ (https://cfl.re/dpa-2025-06-20). Die verlinkte PDF-Datei der v6.4 war aus der Arbeitsumgebung nicht abrufbar – Inhalt der PDF **nicht geprüft**; der Inhaber lädt sie herunter und bewahrt sie datiert auf. Inhalt laut Orchestrator (`docs/legal/PRE_REVIEW.md`): Standardvertragsklauseln Modul 2/3; Klausel 6.4: Cloudflare hält das EU-US Data Privacy Framework ein, sonst gelten die Standardvertragsklauseln. Speicherdauer der Cloudflare-Protokolle aus der Cloudflare-Dokumentation übernehmen (offen). Die Anwendung selbst läuft nicht über Cloudflare (DNS ohne Proxy, Review L8) | **vom Inhaber angenommen** (1. Nov. 2026): DPA ist Teil des Self-Serve Subscription Agreement; datierte PDF-Kopie der v6.4 aufbewahren (frühere Notiz „v6.3“ in `docs/legal/LAUNCH_COMPLIANCE.md` ist überholt) |
| **Server-Hosting der Anwendung** | Betrieb von Anwendung, Datenbank, temporären Dateien | alle oben unter „Anwendung“ genannten Daten | immer | EU (**geplant**, `ops/RUNBOOK.md`); Anbieter `[[BUSINESS_ID_PENDING]]` | **offen** – Anbieter wählen (EU), AVV abschließen |

Ohne diese Einstellungen (Standard) verlässt bei der Zuordnung nichts den Server (heuristischer Vorschlag), und E-Mails werden
nur in der Konsole ausgegeben (nur Entwicklung).

## Für die Datenschutzhinweise noch zu klären (Inhaber / rechtliche Prüfung)

- Verantwortlicher und Kontakt: `[[BUSINESS_ID_PENDING]]`.
- Rechtsgrundlagen je Verarbeitung und berechtigte Interessen (PRE_REVIEW 2.3, 2.4; Vorschlag dort, Q8).
- Rollen: für hochgeladene Rechnungsdaten ist Ablaufwerk voraussichtlich Auftragsverarbeiter des Kunden (Q1); Entwurf `content/legal/avv-entwurf.md`.
- Verzeichnis der Verarbeitungstätigkeiten (Art. 30) aus dieser Liste erstellen (PRE_REVIEW 10.1).
- Ablauf bei Datenschutzverletzungen (PRE_REVIEW 10.2).
- AVV/DPA-Status siehe Tabelle „Dienstleister“ (alle offen); Garantien für die Drittlandübermittlung (Anthropic, Cloudflare).
- Begründung der 3-Jahres-Frist für Einwilligungs- und Widerrufsnachweise durch Fachberatung bestätigen.
- Sitz und Vertragspartner der Dienstleister aus den Verträgen übernehmen (beim Schreiben dieser Liste waren deren Rechtsseiten
  aus der Arbeitsumgebung nicht abrufbar).
