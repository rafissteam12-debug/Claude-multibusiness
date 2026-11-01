---
title: "Allgemeine Geschäftsbedingungen Belegbrücke – Entwurf"
version: "agb-draft-2"
status: "Entwurf – nicht freigegeben, vor Verwendung anwaltlich prüfen. Von einem KI-Agenten erstellt, keine Rechtsberatung. Nicht veröffentlicht, nicht vereinbart."
last_checked: "2026-11-01"
code_state: "main 9eb2720"
---

# Allgemeine Geschäftsbedingungen (AGB) für Belegbrücke

**Version `agb-draft-2`**

> **Entwurf – nicht freigegeben, vor Verwendung anwaltlich prüfen.**
> Dieser Text wurde von einem KI-Agenten aus dem tatsächlichen Stand von Code und Betrieb zusammengestellt
> (`contracts/api.md`, `contracts/mapping.md`, `contracts/brand.md`, `app/`, `ops/RUNBOOK.md`). Er ist keine Rechtsberatung.
> Abschnitte, die mit **„Formulierung anwaltlich prüfen“** markiert sind, sind ausdrücklich nur Platzhalter-Formulierungen.
> Hinweise in grau abgesetzten Kästen („Hinweis zur Prüfung“) richten sich an die prüfende Person und werden vor
> einer Veröffentlichung entfernt.
>
> **Geprüfte Normen** (amtlicher Text auf gesetze-im-internet.de, geöffnet am 1. Nov. 2026):
> § 14 BGB (https://www.gesetze-im-internet.de/bgb/__14.html), § 276 Abs. 3 BGB
> (https://www.gesetze-im-internet.de/bgb/__276.html), § 307 BGB (https://www.gesetze-im-internet.de/bgb/__307.html),
> § 309 Nr. 7 BGB (https://www.gesetze-im-internet.de/bgb/__309.html), § 310 Abs. 1 BGB
> (https://www.gesetze-im-internet.de/bgb/__310.html), § 14 ProdHaftG (https://www.gesetze-im-internet.de/prodhaftg/__14.html),
> § 14b Abs. 1 UStG (https://www.gesetze-im-internet.de/ustg_1980/__14b.html).
> **Nicht am Originaltext geprüft:** DSGVO-Artikel (EUR-Lex-Artikeltext aus der Arbeitsumgebung nicht abrufbar, siehe
> `content/legal/avv-entwurf.md`). Das Geprüfte belegt nur den Wortlaut der Normen, nicht die Wirksamkeit dieser Klauseln.

## § 1 Anbieter, Geltungsbereich, nur für Unternehmer

1. Anbieter des Dienstes „Belegbrücke“ ist `[[BUSINESS_ID_PENDING]]` („Ablaufwerk“, „wir“).
2. Diese AGB gelten für alle Verträge über die Nutzung von Belegbrücke, im kostenlosen wie in bezahlten Tarifen.
3. Belegbrücke richtet sich **ausschließlich an Unternehmer im Sinne von § 14 BGB**, also an natürliche oder juristische
   Personen oder rechtsfähige Personengesellschaften, die bei Abschluss des Vertrags in Ausübung ihrer gewerblichen oder
   selbständigen beruflichen Tätigkeit handeln. **Verbraucher können keinen Vertrag schließen.**
4. Bei der Registrierung bestätigt der Kunde, dass er Belegbrücke ausschließlich für sein Unternehmen nutzt. Wir dürfen
   einen Nachweis der Unternehmereigenschaft verlangen und ein Konto sperren oder löschen, wenn die Bestätigung nicht zutrifft.
5. Abweichende Geschäftsbedingungen des Kunden gelten nicht, auch wenn wir ihnen nicht ausdrücklich widersprechen.
6. Der kostenlose „E-Rechnung-Check“ auf der Website (Prüfung einer einzelnen Datei ohne Konto) ist nicht Gegenstand
   dieser AGB, soweit nicht anders angegeben; für ihn gelten § 5 (Bedeutung der Prüfung) und § 10 (Haftung) entsprechend.

> Hinweis zur Prüfung: Ob die B2B-Bestätigung per Kontrollkästchen genügt und wie mit Verbrauchern umzugehen ist, die
> sich trotzdem anmelden, ist Frage Q15 (`docs/legal/REVIEW_PACKAGE.md`). Ob § 1 Nr. 6 den Check wirksam erfasst,
> ohne dass dort AGB einbezogen werden: prüfen lassen.

## § 2 Vertragsschluss, Konto

1. Die Darstellung von Belegbrücke auf der Website ist kein bindendes Angebot.
2. Der Kunde gibt seine E-Mail-Adresse an und erhält einen Anmeldelink. Mit dem Klick auf den Bestätigungsknopf der
   Seite, die der Anmeldelink öffnet, nach Setzen der Kontrollkästchen zu diesen AGB, zur B2B-Nutzung und zum Vertrag über die
   Auftragsverarbeitung (AVV), gibt der Kunde ein Angebot ab. Der Vertrag kommt zustande, wenn wir das Konto anlegen;
   das Konto wird sofort angelegt und der Kunde ist angemeldet.
3. Wir speichern je Konto die Version der akzeptierten AGB und des AVV mit Zeitpunkt sowie den Zeitpunkt der
   B2B-Bestätigung. Der Kunde sieht diese Angaben in seinem Datenexport (Profil, „Daten herunterladen (JSON)“).
   Den Vertragstext speichern wir nicht gesondert für den Kunden; die jeweils geltende Fassung steht unter `/agb/`
   und kann gespeichert oder gedruckt werden.
4. Je Unternehmen ein Konto; die Zugangsdaten (Zugriff auf das E-Mail-Postfach) hält der Kunde geheim. Handlungen über
   sein Konto muss sich der Kunde zurechnen lassen, soweit er den Missbrauch zu vertreten hat.
5. Vertragssprache ist Deutsch.

> Hinweis zur Prüfung: Ob ein Vertragstext-Archiv für den Kunden nötig ist (z. B. PDF der Fassung in der Bestätigungs-E-Mail),
> ist offen. § 312i BGB (Pflichten im elektronischen Geschäftsverkehr) wurde nicht am Originaltext geprüft.

## § 3 Leistungen

1. Belegbrücke ist ein **technischer Konverter**. Der Kunde lädt einen Rechnungsexport (CSV oder XLSX) hoch. Belegbrücke
   schlägt eine Zuordnung der Spalten zu Rechnungsfeldern vor; der Kunde prüft und bestätigt sie. Belegbrücke erzeugt
   daraus E-Rechnungen in den Formaten XRechnung (CII-Syntax) und/oder ZUGFeRD (PDF/A-3 mit eingebettetem XML),
   prüft jede erzeugte Datei technisch (§ 5) und stellt einen **Prüfbericht** sowie die gültigen Dateien zum Download bereit.
   Zusätzlich kann ein lesbares PDF erzeugt werden; es ist ausdrücklich als „keine E-Rechnung“ gekennzeichnet.
2. Belegbrücke ist ein technisches Werkzeug. Inhalt der Rechnung, Umsatzsteuer und Pflichten bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung.
3. Insbesondere schulden wir **nicht**: die steuerliche oder rechtliche Richtigkeit der Rechnungsinhalte (z. B. Steuersätze,
   Steuerbefreiungen, Pflichtangaben), den Versand der Rechnungen an Empfänger, die Archivierung der Rechnungen, die
   Anbindung an Buchhaltungs- oder ERP-Systeme oder Beratung.
4. Die Verkäuferangaben (Unternehmensprofil) pflegt der Kunde in seinem Profil; sie haben bei der Umwandlung Vorrang vor
   Werten aus der hochgeladenen Datei.
5. **Grenzen je Nutzung** (Stand des Codes): höchstens 10 MB je Upload, höchstens 500 Rechnungen je Datei, höchstens
   3 gleichzeitig laufende Umwandlungen und 60 Uploads pro Stunde je Konto. Wir dürfen diese Grenzen ändern, wenn der
   Dienst dadurch für den vereinbarten Zweck nutzbar bleibt.
6. Wir dürfen den Dienst weiterentwickeln (z. B. neue Formate, aktualisierte Prüfregeln), soweit die vereinbarten
   Kernleistungen nach Nr. 1 erhalten bleiben.

## § 4 Tarife, Preise, Zahlung

1. **Kostenloser Tarif („free“):** bis zu 3 gültige Rechnungen je Kalendermonat. Hochladen, Zuordnen und Prüfen sind
   darüber hinaus möglich; gezählt werden nur gültige Rechnungen, die zum Download angeboten werden.
2. **Bezahlte Tarife:** „Start“ (bis zu 30 gültige Rechnungen je Kalendermonat) und „Business“ (bis zu 300 gültige
   Rechnungen je Kalendermonat). Preise: `[[BUSINESS_ID_PENDING]]`. Abrechnungszeitraum, Fälligkeit, Zahlungsarten,
   Umsatzsteuer-Ausweis und Folgen eines Zahlungsverzugs: `[[BUSINESS_ID_PENDING]]`.
3. Der Kalendermonat richtet sich nach deutscher Zeit. Nicht genutzte Kontingente verfallen am Monatsende.
4. Ein Tarifwechsel wird `[[BUSINESS_ID_PENDING]]` wirksam.
5. Für den kostenlosen Tarif besteht kein Anspruch auf Fortbestand; wir können ihn mit einer Frist von
   `[[BUSINESS_ID_PENDING]]` ändern oder einstellen.

> Hinweis zur Prüfung: Eine Zahlungsanbindung gibt es im Code noch nicht (nur die Spalte `plan`). Kontingente laut
> `contracts/api.md`, Abschnitt „Plans“. Preisänderungsklausel für laufende bezahlte Verträge: Formulierung anwaltlich prüfen.

## § 5 Bedeutung der Prüfung („gültig“)

1. Eine Datei gilt bei Belegbrücke als **„gültig“**, wenn die technischen Prüfungen ohne Fehler durchlaufen wurden:
   Schema (XSD), Regeln der europäischen Norm EN 16931 und – für XRechnung – die XRechnung-Regeln; im Live-Betrieb
   zusätzlich der KoSIT-Validator. Für ZUGFeRD wird außerdem die PDF/A-3-Konformität geprüft, soweit das Prüfwerkzeug
   verfügbar ist. Nur gültige Dateien bieten wir als E-Rechnung an.
2. Eine Prüfung, die nicht ausgeführt werden konnte, wird im Prüfbericht als **„übersprungen“ mit Grund** angezeigt und
   nie als bestanden gewertet.
3. Die Prüfung verwendet die in Belegbrücke **festgelegten Versionen der Prüfregeln** (Regeldateien im Dienst, mit Version
   und Datum dokumentiert). Neuere Regelversionen, Regeln einzelner Empfänger oder Portale und branchenspezifische
   Vorgaben sind nicht Gegenstand der Prüfung, solange wir sie nicht übernommen haben.
4. „Gültig“ heißt: die Datei erfüllt diese technischen Regeln. Es heißt **nicht**, dass die Rechnung inhaltlich, steuerlich
   oder rechtlich richtig ist, und **nicht**, dass ein Empfänger oder dessen System die Datei annimmt.
5. Werte, die der Kunde hochlädt, werden nicht auf inhaltliche Richtigkeit geprüft. Rechenprüfungen (z. B. Summen)
   beziehen sich nur auf die Werte in der Datei.

> Hinweis zur Prüfung: Ob die Anzeige „gültig“ eine Beschaffenheitsvereinbarung oder Garantie begründet, ist Frage Q16.
> Validitätsregel: `contracts/mapping.md`, „Validity rule“; Regelversionen: `engine/rules/VERSIONS.md`.

## § 6 Pflichten des Kunden

1. Der Kunde stellt richtige und vollständige Daten bereit (Rechnungsexport und Unternehmensprofil) und prüft die
   vorgeschlagene Zuordnung, bevor er umwandelt.
2. Der Kunde **prüft jede erzeugte Rechnung selbst** auf Inhalt, Umsatzsteuer und Pflichtangaben, bevor er sie versendet,
   oder lässt sie von seiner Steuerberatung prüfen.
3. Der Kunde lädt nur Daten hoch, die er rechtmäßig verarbeiten und an uns übermitteln darf, insbesondere personenbezogene
   Daten seiner Kunden und Ansprechpartner, und erfüllt seine Informationspflichten gegenüber diesen Personen.
4. Der Kunde lädt keine Schadsoftware hoch, umgeht keine technischen Grenzen und nutzt den Dienst nicht automatisiert
   außerhalb der vorgesehenen Oberfläche, soweit wir das nicht erlauben.
5. Der Kunde **lädt seine Ergebnisse innerhalb von 24 Stunden herunter** und archiviert seine Rechnungen selbst.
   Belegbrücke ist kein Archiv. (Unternehmer müssen Rechnungen nach § 14b Abs. 1 UStG grundsätzlich acht Jahre
   aufbewahren; das ist Sache des Kunden.)

## § 7 Datenverarbeitung, Auftragsverarbeitung, Aufbewahrung

1. Soweit wir für den Kunden personenbezogene Daten aus seinen Rechnungsexporten verarbeiten, gilt der **Vertrag über die
   Auftragsverarbeitung (AVV), Version `avv-draft-1`**, den der Kunde zusammen mit diesen AGB abschließt. Bei Widersprüchen
   geht der AVV für die Verarbeitung personenbezogener Daten vor.
2. Für Konto- und Profildaten des Kunden sind wir selbst verantwortlich; Einzelheiten stehen in den Datenschutzhinweisen.
3. **Aufbewahrung, wie im Dienst eingebaut:**
   - Hochgeladene Datei (Rohdatei), Dateiname und Beispielwerte: gelöscht nach erfolgreicher Umwandlung (mindestens eine
     gültige Datei angeboten), sonst spätestens nach 24 Stunden.
   - Erzeugte Dateien (XRechnung, ZUGFeRD, lesbares PDF, ZIP), Ergebnisse je Rechnung und Fehlermeldungen: nach 24 Stunden.
   - Gespeicherte Zuordnungen (ohne Zellinhalte), Unternehmensprofil, Auftragsdaten ohne Inhalte und Nutzungszähler:
     solange das Konto besteht.
   - Konten ohne Anmeldung seit 12 Monaten werden mit allen Daten gelöscht.
   - Wir erstellen keine Backups der Kundendaten. Nach Ablauf der Fristen lassen sich Daten nicht wiederherstellen.
4. Wir nutzen die Inhalte der Rechnungsexporte nicht für eigene Zwecke und nicht zum Training von KI-Modellen.

## § 8 KI-Vorschlag der Zuordnung

1. Standardmäßig erstellt Belegbrücke den Zuordnungsvorschlag **ohne KI** auf dem eigenen Server (regelbasiert); dabei
   verlassen keine Daten den Server.
2. Ist der KI-Vorschlag eingeschaltet, sendet Belegbrücke an den KI-Anbieter (derzeit Anthropic) nur Spaltennamen,
   die **Form** der Werte aus bis zu fünf Beispielzeilen (z. B. „31.10.2026“ wird zu „dd.dd.dddd“), statistische
   Spaltenhinweise, die Zeilenzahl und Standardwerte aus dem Profil (Steuersatz, Steuerkategorie, Einheit).
3. **Echte Beispielwerte** werden nur gesendet, wenn der Kunde dies für die jeweilige Datei ausdrücklich einschaltet
   („Echte Beispielwerte an die KI senden“).
4. Der KI-Anbieter kann die Anfrage **außerhalb der EU** verarbeiten (laut seiner Dokumentation in beliebigen Regionen
   oder in den USA; Speicherung in den USA). Einzelheiten und Garantien: AVV, Anlage 2, und Datenschutzhinweise.
5. Der KI-Vorschlag ist ein Vorschlag. Der Kunde bestätigt oder korrigiert die Zuordnung, bevor umgewandelt wird.
   Fällt die KI aus, nutzt Belegbrücke den regelbasierten Vorschlag.

> Hinweis zur Prüfung: Im Live-Betrieb wird die KI erst nach rechtlicher Freigabe der Übermittlung eingeschaltet
> (Schutz `AI_TRANSFER_CLEARED` in der Anwendung, in Arbeit). Ob die Wertformen personenbezogene Daten sind: Frage Q3;
> Rechtsgrundlage der Übermittlung: Q4.

## § 9 Verfügbarkeit, Wartung

1. Wir bemühen uns um einen störungsfreien Betrieb, **sagen aber keine bestimmte Verfügbarkeit zu**. Ein
   Service-Level-Agreement besteht nicht.
2. Der Dienst kann für Wartung, Sicherheitsupdates oder bei Störungen außerhalb unseres Einflussbereichs (z. B. Ausfälle
   von Rechenzentrum, Netz oder Dienstleistern) vorübergehend nicht verfügbar sein. Wir kündigen geplante Wartungen
   nach Möglichkeit vorher an.
3. Wird ein Auftrag durch einen Neustart unterbrochen, wird er als fehlgeschlagen markiert. Der Kunde kann die
   Umwandlung erneut starten, solange die hochgeladene Datei noch vorhanden ist (höchstens 24 Stunden), oder die Datei
   neu hochladen.

> Hinweis zur Prüfung: Ob für bezahlte Tarife eine Mindestverfügbarkeit angeboten werden soll, ist eine Entscheidung des
> Inhabers; eine Überwachung mit Messwerten gibt es derzeit nicht, daher hier keine Zahl.

## § 10 Haftung

**Formulierung anwaltlich prüfen.** (Rahmen: § 307 BGB gilt auch gegenüber Unternehmern, § 310 Abs. 1 BGB; die Wertungen
von § 309 Nr. 7 BGB werden im B2B-Verkehr über § 307 berücksichtigt; § 276 Abs. 3 BGB; § 14 ProdHaftG.)

1. Wir haften unbeschränkt
   a) bei Vorsatz und grober Fahrlässigkeit, auch unserer gesetzlichen Vertreter und Erfüllungsgehilfen;
   b) für Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit;
   c) nach dem Produkthaftungsgesetz;
   d) soweit wir eine Garantie übernommen haben (eine solche Garantie geben wir mit diesen AGB nicht).
2. Bei **leicht fahrlässiger** Verletzung einer **wesentlichen Vertragspflicht** (Kardinalpflicht) haften wir nur für den
   vertragstypischen, bei Vertragsschluss vorhersehbaren Schaden. Wesentliche Vertragspflichten sind Pflichten, deren
   Erfüllung die ordnungsgemäße Durchführung des Vertrags erst ermöglicht und auf deren Einhaltung der Kunde regelmäßig
   vertrauen darf.
3. Im Übrigen ist die Haftung für leichte Fahrlässigkeit ausgeschlossen.
4. Höhenbegrenzung bei Nr. 2: `[[BUSINESS_ID_PENDING]]` (z. B. gekoppelt an die gezahlten Entgelte; für den kostenlosen
   Tarif gesondert zu regeln). Formulierung anwaltlich prüfen.
5. Wir haften nicht für Folgen, die darauf beruhen, dass der Kunde Pflichten aus § 6 nicht erfüllt hat, insbesondere
   für unrichtige Rechnungsinhalte aus seinen Daten, für die Ablehnung einer gültigen Datei durch einen Empfänger
   (§ 5 Nr. 4) oder für den Verlust von Daten, die nicht innerhalb von 24 Stunden heruntergeladen wurden (§ 7 Nr. 3);
   Nr. 1 bleibt unberührt.
6. Die Haftungsbeschränkungen gelten auch für unsere gesetzlichen Vertreter, Beschäftigten und Erfüllungsgehilfen.

> Hinweis zur Prüfung: Frage Q16 – Reichweite der Begrenzung für falsche Prüfergebnisse; eigene Regelung für den
> kostenlosen Tarif (ob Haftungsmaßstäbe unentgeltlicher Verträge herangezogen werden können) – nur als Frage,
> keine Norm am Originaltext geprüft.

## § 11 Laufzeit, Kündigung

1. Der Vertrag über den kostenlosen Tarif läuft auf unbestimmte Zeit. Beide Seiten können ihn jederzeit ohne Frist
   kündigen; der Kunde zum Beispiel, indem er sein Konto löscht (§ 12).
2. Laufzeit und Kündigungsfristen der bezahlten Tarife: `[[BUSINESS_ID_PENDING]]`.
3. Das Recht zur außerordentlichen Kündigung aus wichtigem Grund bleibt unberührt. Ein wichtiger Grund liegt für uns
   insbesondere vor, wenn der Kunde kein Unternehmer ist (§ 1 Nr. 3), gegen § 6 Nr. 3 oder Nr. 4 verstößt oder mit
   Zahlungen in Verzug ist (`[[BUSINESS_ID_PENDING]]`).
4. Kündigungen bedürfen der Textform (z. B. E-Mail); die Löschung des Kontos in der Anwendung genügt.
5. Ein Konto ohne Anmeldung seit 12 Monaten wird gelöscht; damit endet der Vertrag.

## § 12 Löschung des Kontos, Datenexport

1. Der Kunde kann sein Konto jederzeit im Profil mit **„Konto löschen“** löschen. Sofort gelöscht werden: Konto, Sitzungen,
   Anmeldelinks, Unternehmensprofil, Zuordnungen, Uploads, erzeugte Dateien, Aufträge und Nutzungszähler.
2. Vor der Löschung kann der Kunde mit **„Daten herunterladen (JSON)“** sein Konto (E-Mail, Tarif, Zeitpunkte, akzeptierte
   AGB- und AVV-Version), das Unternehmensprofil, die Zuordnungen (ohne Zellinhalte) und die Nutzungszähler herunterladen.
3. Eine Anmeldung zu E-Mail-Hinweisen ist davon getrennt; sie endet über den Abmeldelink in jeder E-Mail.
4. Bereits gezahlte Entgelte bei Löschung während einer bezahlten Laufzeit: `[[BUSINESS_ID_PENDING]]`.

## § 13 Änderungen dieser AGB

1. Jede Fassung dieser AGB hat eine **Versionskennung** (diese Fassung: `agb-draft-2`). Eine geänderte Fassung erhält
   eine neue Versionskennung.
2. Nach einer Änderung wird der Kunde bei der nächsten Anmeldung gebeten, die neue Fassung zu akzeptieren. Bis dahin gilt
   die zuletzt akzeptierte Fassung. Ohne Annahme kann der Kunde den Dienst nicht weiter nutzen, aber sein Konto löschen
   und seine Daten exportieren.
3. Änderungen der Preise laufender bezahlter Verträge: `[[BUSINESS_ID_PENDING]]`; Formulierung anwaltlich prüfen.

> Hinweis zur Prüfung: Die Anwendung fragt bei abweichender Version erneut nach und speichert Version und Zeitpunkt
> (`contracts/api.md`, `/api/v1/auth/callback`). Ob eine Mitteilung vorab per E-Mail nötig ist, ist offen.

## § 14 Anwendbares Recht, Gerichtsstand

1. Es gilt das Recht der Bundesrepublik Deutschland unter Ausschluss des UN-Kaufrechts. Formulierung anwaltlich prüfen.
2. Gerichtsstand: `[[BUSINESS_ID_PENDING]]` (soweit zulässig, Sitz des Anbieters). Formulierung anwaltlich prüfen.

## § 15 Schlussbestimmungen

1. Sollte eine Bestimmung dieser AGB unwirksam sein, bleiben die übrigen Bestimmungen wirksam. An die Stelle der
   unwirksamen Bestimmung tritt die gesetzliche Regelung.
2. Der Kunde kann Rechte aus diesem Vertrag nur mit unserer Zustimmung abtreten; § 354a HGB bleibt unberührt
   (nicht am Originaltext geprüft).
3. Mündliche Nebenabreden bestehen nicht. Erklärungen nach diesem Vertrag genügen in Textform.
4. Anlage: Vertrag über die Auftragsverarbeitung (AVV), Version `avv-draft-1` (`content/legal/avv-entwurf.md`).

---

## Annahme in der Anwendung

Die Anwendung zeigt bei der ersten Anmeldung (und nach jeder neuen Versionskennung) ein Pflicht-Kontrollkästchen mit
genau diesem Text und speichert ihn wörtlich unter der Versionskennung (`app/legal_texts/`); gespeichert werden je Konto
Versionskennung und Zeitpunkt der Annahme, sichtbar im Datenexport.

Checkbox-Text agb-draft-2

```text
Ich akzeptiere die Allgemeinen Geschäftsbedingungen (Entwurf, Version agb-draft-2).
```

Die B2B-Bestätigung bleibt ein eigenes Kontrollkästchen mit unverändertem Text:

```text
Ich nutze Belegbrücke ausschließlich für mein Unternehmen (B2B).
```

Der Text für den AVV steht in `content/legal/avv-entwurf.md` („Checkbox-Text avv-draft-1“).
