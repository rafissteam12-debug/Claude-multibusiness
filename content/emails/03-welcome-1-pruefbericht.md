Betreff: So lesen Sie einen Prüfbericht für E-Rechnungen
Vorschautext: Was BR-DE-15 bedeutet – und die vier Fehler, die in alten Rechnungen typisch sind.

# So lesen Sie einen Prüfbericht

Guten Tag,

danke für Ihre Bestätigung. In dieser E-Mail geht es um eine Frage: Was steht in einem Prüfbericht – und was tun Sie damit?

## Der Aufbau

Ein Prüfbericht des E-Rechnung-Checks hat mehrere **Prüfschichten**:

1. **XSD** – Ist die Datei technisch korrekt aufgebaut?
2. **EN 16931** – Erfüllt sie die Regeln der europäischen Norm?
3. **XRechnung** – Erfüllt sie die deutschen Zusatzregeln? (nur bei XRechnung)
4. **KoSIT** – Prüfung mit dem offiziellen Validator der KoSIT.

Jede Schicht zeigt **bestanden**, **Fehler** oder **übersprungen**. Übersprungen heißt: nicht geprüft. Das ist nie dasselbe wie bestanden. Der Bericht nennt immer den Grund.

**Fehler** machen die Datei ungültig. **Warnungen** sollten Sie lesen, sie machen die Datei aber nicht ungültig.

## Eine Fehlermeldung lesen

Jeder Fehler hat eine **Regelkennung**, zum Beispiel `BR-DE-15`, eine deutsche Erklärung und eine Fundstelle in der Datei.

- `BR-DE-…` sind Regeln aus dem deutschen Standard XRechnung.
- `BR-CO-…`, `BR-…` sind Regeln der europäischen Norm.
- `BT-…` sind die Felder, um die es geht, zum Beispiel BT-10 für die Käuferreferenz.

## Vier Fehler, die in Rechnungen aus älteren Programmen typisch sind

- **BR-DE-15 – Käuferreferenz fehlt.** Feld BT-10 ist in einer XRechnung Pflicht. Bei Behörden steht dort die Leitweg-ID.
- **BR-CO-25 – Zahlungsbedingung fehlt.** Bei offenem Betrag braucht es ein Fälligkeitsdatum (BT-9) oder einen Text zu den Zahlungsbedingungen (BT-20).
- **BR-CO-26 – Keine Kennung des Verkäufers.** Mindestens USt-IdNr., Registernummer oder Verkäuferkennung muss enthalten sein.
- **BR-CO-15 – Summen passen nicht.** Brutto muss genau Netto plus Steuer ergeben. Oft ist es eine Rundungsdifferenz von einem Cent.

Diese Liste beruht auf den Regeln selbst, nicht auf einer Auswertung von Kundendaten. Ausführlicher im Ratgeber „Pflichtfelder der E-Rechnung“: {{ site_url }}/ratgeber/pflichtfelder-e-rechnung

## Was Sie mit dem Bericht tun

Die meisten Fehler lassen sich nicht in der XML-Datei beheben, sondern dort, wo die Rechnung entsteht: in Ihren Stammdaten oder Ihrer Rechnungsvorlage. Ergänzen Sie dort die fehlende Angabe und erzeugen Sie die Datei neu.

[Nächste Datei prüfen]({{ check_url }})

In ein paar Tagen erklären wir, wie Belegbrücke aus Ihrem bestehenden Rechnungsexport E-Rechnungen macht.

Viele Grüße
Ablaufwerk

[Abmelden]({{ unsubscribe_url }})

{% include "_footer.md" %}
