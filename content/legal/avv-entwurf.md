---
title: "Vertrag über die Auftragsverarbeitung (AVV) – Entwurf"
status: "Entwurf – vor Verwendung anwaltlich prüfen. Von einem KI-Agenten erstellt, keine Rechtsberatung. Nicht veröffentlicht, nicht abgeschlossen."
last_checked: "2026-11-01"
code_state: "main 49bb0f2"
---

# Vertrag über die Auftragsverarbeitung (AVV) – Entwurf

> **Entwurf – vor Verwendung anwaltlich prüfen.** Dieser Text wurde von einem KI-Agenten aus dem tatsächlichen
> Stand von Code und Betrieb zusammengestellt. Er ist keine Rechtsberatung und kein fertiger Vertrag.
>
> **Artikelangaben nicht am Originaltext geprüft:** Der amtliche Text der DSGVO
> (https://eur-lex.europa.eu/eli/reg/2016/679/oj) war aus der Arbeitsumgebung nur bis zu den Erwägungsgründen abrufbar.
> Alle Verweise auf Artikel (Art. 28, 29, 32–36, 44 ff. DSGVO) stammen aus allgemeinem Wissen und **müssen von der
> prüfenden Person am Originaltext abgeglichen werden** (vgl. `docs/legal/PRE_REVIEW.md`, Abschnitt 0, Fragen Q1–Q2).
>
> Ob Ablaufwerk für die hochgeladenen Rechnungsdaten Auftragsverarbeiter ist (und für den kostenlosen E-Rechnung-Check
> ohne Konto ebenfalls), ist eine offene Rechtsfrage (Q1). Dieser Entwurf geht von der Auftragsverarbeitung aus.

## Parteien

- **Verantwortlicher („Kunde“):** das Unternehmen, das ein Konto bei Belegbrücke anlegt und Rechnungsexporte hochlädt.
- **Auftragsverarbeiter („Ablaufwerk“):** `[[BUSINESS_ID_PENDING]]`.

Der Vertrag wird elektronisch zusammen mit den AGB abgeschlossen (Anlage zu den AGB). Form und Abschlussweg: prüfen (Q2).

## § 1 Gegenstand und Dauer

1. **Gegenstand:** Umwandlung der vom Kunden hochgeladenen Rechnungsexporte (CSV/XLSX) in E-Rechnungen
   (XRechnung, ZUGFeRD), deren technische Prüfung (Validierung) und die Bereitstellung der Ergebnisse zum Download
   mit dem Dienst Belegbrücke.
2. **Dauer:** solange das Konto des Kunden besteht. Nach Ende des Kontos gelten § 9 (Löschung) und die dort
   genannten Fristen. Konten ohne Anmeldung seit 12 Monaten werden mit allen Daten gelöscht.

## § 2 Art und Zweck der Verarbeitung

- **Art:** Hochladen und kurzzeitiges Speichern der Datei, Lesen der Tabelle, Zuordnung der Spalten zu Rechnungsfeldern
  (Vorschlag, Bestätigung durch den Kunden), Erzeugen der E-Rechnung und eines lesbaren PDF, Prüfung, Bereitstellung
  zum Download, Löschung.
- **Zweck:** ausschließlich die Erzeugung und Prüfung der E-Rechnungen für den Kunden. Keine Nutzung der Inhalte für
  eigene Zwecke von Ablaufwerk, kein Training von KI-Modellen, keine Weitergabe zu Werbezwecken.

## § 3 Art der Daten und Kategorien betroffener Personen

**Daten (aus den Rechnungsexporten des Kunden):**

- Namen und Anschriften von Rechnungsempfängern (Käufer) und Lieferorten;
- E-Mail-Adressen, Telefonnummern und Namen von Ansprechpartnern;
- Käuferreferenzen, Bestell- und Kundennummern, USt-IdNr. der Käufer;
- Rechnungsinhalte: Rechnungsnummer und -datum, Leistungen, Mengen, Preise, Beträge, Steuersätze, Zahlungsbedingungen,
  Bankverbindungen;
- Fehlermeldungen der Prüfung, soweit sie Werte aus der Datei enthalten.

**Betroffene Personen:** Kunden des Kunden (Käufer, soweit natürliche Personen, z. B. Einzelunternehmer),
deren Ansprechpartner und Beschäftigte; Ansprechpartner des Kunden selbst, soweit sie in den Rechnungen stehen.

Nicht Gegenstand dieses Vertrags: die Konto- und Profildaten des Kunden selbst (Login-E-Mail, Unternehmensprofil) und
die Anmeldung zu E-Mail-Hinweisen; dafür ist Ablaufwerk selbst verantwortlich (siehe Datenschutzhinweise).

## § 4 Weisungen

1. Ablaufwerk verarbeitet die Daten nur auf dokumentierte Weisung des Kunden. Die Weisungen sind abschließend in diesem
   Vertrag, den AGB und den Einstellungen festgelegt, die der Kunde in der Anwendung wählt (Zuordnung, Formate,
   Einstellung „Echte Beispielwerte an die KI senden“).
2. Hält Ablaufwerk eine Weisung für rechtswidrig, informiert es den Kunden unverzüglich.

## § 5 Vertraulichkeit

Personen, die bei Ablaufwerk Zugang zu den Daten haben können, sind zur Vertraulichkeit verpflichtet. Ablaufwerk greift
nicht auf die Inhalte zu, außer soweit es für den Betrieb oder eine Anfrage des Kunden zwingend nötig ist.

## § 6 Technische und organisatorische Maßnahmen

Siehe **Anlage 1 (TOMs)**. Ablaufwerk darf die Maßnahmen an den Stand der Technik anpassen, wenn das Schutzniveau nicht sinkt.

## § 7 Unterauftragsverarbeiter

1. Der Kunde stimmt den Unterauftragsverarbeitern in **Anlage 2** zu.
2. Ablaufwerk informiert den Kunden vorab über Änderungen; der Kunde kann widersprechen. Frist und Folge eines
   Widerspruchs (z. B. Kündigungsrecht): prüfen.
3. Ablaufwerk verpflichtet Unterauftragsverarbeiter vertraglich auf ein gleichwertiges Schutzniveau.

## § 8 Unterstützung des Kunden

Ablaufwerk unterstützt den Kunden im Rahmen der Möglichkeiten des Dienstes

- bei Anfragen betroffener Personen (Auskunft, Berichtigung, Löschung usw.): Rechnungsdaten liegen bei Ablaufwerk
  höchstens 24 Stunden; die Berichtigung erfolgt in den Quelldaten des Kunden;
- bei Sicherheit der Verarbeitung, Meldungen von Datenschutzverletzungen und Datenschutz-Folgenabschätzungen.
  Ablaufwerk meldet dem Kunden eine Verletzung des Schutzes der Auftragsdaten **unverzüglich** nach Kenntnis.
  (Ein Ablauf für Datenschutzverletzungen fehlt noch in `ops/RUNBOOK.md`; PRE_REVIEW 10.2.)

## § 9 Löschung und Rückgabe

Die Löschung ist im Dienst eingebaut (Code: `app/jobs.py`, `contracts/api.md`):

| Daten | Löschung |
| --- | --- |
| Hochgeladene Datei (Rohdatei) und Beispielwerte | nach erfolgreicher Umwandlung sofort, sonst spätestens nach 24 Stunden |
| Erzeugte Dateien (XRechnung, ZUGFeRD, lesbares PDF, ZIP) | nach 24 Stunden |
| Ergebnisse und Fehlermeldungen eines Auftrags | nach 24 Stunden |
| Alles zum Konto (auch Zuordnungen und Aufträge) | sofort mit „Konto löschen“; automatisch nach 12 Monaten ohne Anmeldung |

**Rückgabe:** Der Kunde lädt seine Ergebnisse innerhalb von 24 Stunden herunter. Die gespeicherten Zuordnungen
(ohne Zellinhalte) und das Profil kann er jederzeit als JSON herunterladen. Es gibt keine Backups, aus denen später
gelöschte Daten wiederhergestellt werden könnten.

## § 10 Nachweise und Kontrollen

Ablaufwerk stellt dem Kunden auf Anfrage die Informationen zur Verfügung, die zum Nachweis der Pflichten nötig sind
(dieser Vertrag, Anlage 1 und 2, Auszüge aus der Betriebsdokumentation). Kontrollen vor Ort nach Absprache mit
angemessener Vorankündigung; Kostenregelung: prüfen.

## § 11 Haftung, Schlussbestimmungen

`[[BUSINESS_ID_PENDING]]` – anwaltlich zu formulieren (Haftung, Vorrang dieses Vertrags vor den AGB bei Widersprüchen,
Gerichtsstand, Schriftform/Textform).

---

## Anlage 1 – Technische und organisatorische Maßnahmen (Stand des Codes)

Nur Maßnahmen, die im Code oder in der Betriebsanleitung stehen. „geplant“ = noch nicht umgesetzt.

**Vertraulichkeit / Zugangskontrolle**
- Transportverschlüsselung: HTTPS über Caddy mit automatischen Zertifikaten; HSTS (`max-age=31536000`) (`ops/Caddyfile`, `app/main.py`).
- Anmeldung ohne Passwort per Einmal-Link; Links gelten 15 Minuten und nur einmal; gespeichert wird nur ein HMAC-Hash des Tokens.
- Sitzungs-Cookie HttpOnly, Secure, SameSite=Lax; Sitzungen laufen nach 7 Tagen ab.
- Schutz vor fremden Anfragen: CSRF-Token und Prüfung der Herkunft (same-origin) für alle ändernden Anfragen.
- Mandantentrennung: jeder Zugriff auf Upload, Zuordnung, Auftrag und Datei prüft, ob er dem angemeldeten Konto gehört.
- Server: eigener Benutzer mit SSH-Schlüssel, Passwort-Login aus, Firewall nur 22/80/443, automatische Sicherheitsupdates (`ops/RUNBOOK.md`, Einrichtung durch den Inhaber).
- Container: schreibgeschütztes Dateisystem, `no-new-privileges`, alle Linux-Capabilities entzogen (`ops/docker-compose.yml`).
- Geheimnisse nur aus Umgebungsvariablen; `.env` mit Rechten 600, nicht im Repository.
- Verschlüsselung der gespeicherten Daten auf dem Datenträger: im Code nicht vorgesehen; hängt vom Hoster ab (prüfen).

**Datenminimierung / Speicherbegrenzung**
- Fristen siehe § 9; Löschlauf alle 10 Minuten in der Anwendung und stündlich als eigener Dienst.
- `PRAGMA secure_delete = ON`: gelöschte Inhalte werden in der Datenbank überschrieben.
- Keine Backups.
- KI-Zuordnung standardmäßig aus (heuristischer Vorschlag ohne Netzwerk). Ist sie eingerichtet, erhält der KI-Dienst
  nur Spaltennamen und die Form der Werte (z. B. „dd.dd.dddd“); echte Werte nur, wenn der Kunde das einschaltet.

**Protokollierung**
- Keine Rechnungsinhalte, keine KI-Anfragen mit Werten, keine Tokens in Protokollen; Fehler nur mit Name der Fehlerklasse.
- Zugriffsprotokoll: IP-Adressen gekürzt, Token, Cookies, Authorization, Referer nicht protokolliert;
  Aufbewahrung 14 Tage (größenbasierte Rotation; strenge Altersgrenze bei Servereinrichtung).
- Keine IP-Adressen im Klartext in der Datenbank; für Rate-Limits nur ein gesalzener Hash (2 Tage).

**Integrität / Verfügbarkeit / Belastbarkeit**
- Prüfung jeder erzeugten Datei vor dem Download (XSD, EN 16931, XRechnung, KoSIT); übersprungene Prüfungen werden als übersprungen angezeigt.
- Sichere XML-Verarbeitung (keine externen Entitäten, kein Netzwerk, Größenlimits vor dem Parsen).
- Größen- und Mengengrenzen (10 MB je Upload, 500 Rechnungen je Datei, 3 gleichzeitige Aufträge, 60 Uploads pro Stunde).
- Healthcheck und automatischer Neustart der Container.

**Organisation**
- Ablauf bei Datenschutzverletzungen: **geplant** (PRE_REVIEW 10.2).
- Verzeichnis der Verarbeitungstätigkeiten: **geplant** (Grundlage: `content/legal/datenschutz-fakten.md`).

## Anlage 2 – Unterauftragsverarbeiter

| Unterauftragsverarbeiter | Leistung | Auftragsdaten betroffen? | Ort | Status |
| --- | --- | --- | --- | --- |
| Server-Hoster `[[BUSINESS_ID_PENDING]]` | Betrieb von Anwendung, Datenbank, temporären Dateien | ja (alle Auftragsdaten, höchstens 24 Stunden) | EU (geplant) | Anbieter wählen, AVV abschließen |
| Anthropic (Vertragspartner für EWR-Kunden laut Commercial Terms: Anthropic Ireland, Limited; Verarbeitung auch durch Anthropic PBC, USA, und weitere Unterauftragsverarbeiter) | KI-Vorschlag der Spaltenzuordnung | **nur wenn die KI eingerichtet ist**; dann Spaltennamen und Form der Werte; echte Beispielwerte nur auf Einschalten durch den Kunden | Verarbeitung „global“ oder „us“, Speicherung „us“; keine EU-Option dokumentiert | DPA über die Commercial Terms; Garantien (Standardvertragsklauseln) prüfen |
| Brevo | E-Mail-Versand (Anmeldelinks, E-Mail-Hinweise) | **nein** – keine Rechnungsdaten | Sitz aus dem Vertrag übernehmen | nur für Kontodaten von Ablaufwerk; nicht Teil dieser Liste, falls die Prüfung das bestätigt |
| Cloudflare | Auslieferung der statischen Website | **nein** – die Anwendung läuft nicht über Cloudflare | – | nicht Teil dieser Liste, falls die Prüfung das bestätigt |

Quellen zu Anthropic (vom Orchestrator am 1. Nov. 2026 geöffnet, `docs/legal/PRE_REVIEW.md`):
https://www.anthropic.com/legal/commercial-terms, https://www.anthropic.com/legal/data-processing-addendum;
Datenstandorte: https://platform.claude.com/docs/en/manage-claude/data-residency (selbst geöffnet).
