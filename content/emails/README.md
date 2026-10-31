# E-Mail-Texte (Entwurf)

Status: Entwurf, nichts versendet. Platzhalter in doppelten geschweiften Klammern
werden von der App gefüllt (Jinja2). `[[BUSINESS_ID_PENDING]]` bleibt stehen, bis die
Geschäftsidentität geklärt ist (CLAUDE.md, Regel 6).

| Datei | Auslöser | Platzhalter |
| --- | --- | --- |
| `01-double-opt-in.md` | `POST /api/v1/subscribe` | `{{ confirm_url }}`, `{{ source_label }}` (z. B. „über den E-Rechnung-Check“), `{{ requested_at }}` |
| `02-magic-link.md` | `POST /api/v1/auth/magic-link` | `{{ login_url }}`, `{{ requested_at }}` |
| `03-welcome-1-pruefbericht.md` | nach Bestätigung, Tag 0 | `{{ check_url }}`, `{{ site_url }}`, `{{ unsubscribe_url }}` |
| `04-welcome-2-belegbruecke.md` | nach Bestätigung, Tag 3 (Vorschlag) | `{{ app_url }}`, `{{ unsubscribe_url }}` |

Format jeder Datei: Zeile `Betreff:`, Zeile `Vorschautext:`, dann der Text in Markdown.
Buttons sind als `[Beschriftung]({{ url }})` geschrieben; die App rendert sie als Button.
Gemeinsamer Fußtext: `_footer.md`.
