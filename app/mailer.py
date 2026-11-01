"""Mailer adapter: `console` (dev/test: prints subject + link, never in prod) and `brevo` (transactional API).

Texts come from content/emails/*.md (format: `Betreff:` line, `Vorschautext:` line, Markdown body with
Jinja placeholders and `{% include "_footer.md" %}`). Loaded once at startup. The footer placeholder
[[BUSINESS_ID_PENDING]] is kept as is.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import jinja2
import markdown

from .helptexts import UnverifiedContent, refuse_unverified
from .settings import CONTENT_DIR, Settings

EMAIL_DIR = CONTENT_DIR / "emails"
TEMPLATES = {
    "optin": "01-double-opt-in.md",
    "login": "02-magic-link.md",
    "welcome1": "03-welcome-1-pruefbericht.md",
    "welcome2": "04-welcome-2-belegbruecke.md",
}
LINK_KEYS = ("login_url", "confirm_url", "unsubscribe_url")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"
log = logging.getLogger("app")


@dataclass
class Mail:
    to: str
    subject: str
    preview: str
    text: str
    html: str
    kind: str
    link: str | None


class MailTemplates:
    """strict=True (default; the app uses it in staging/prod) refuses any mail text containing `[prüfen`."""

    def __init__(self, directory: Path = EMAIL_DIR, strict: bool = True):
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(directory)),
                                      autoescape=False, undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
        self.raw: dict[str, tuple[str, str, str]] = {}
        for kind, name in TEMPLATES.items():
            text = (directory / name).read_text(encoding="utf-8")
            for part in [name] + re.findall(r'{%\s*include\s+"([^"]+)"', text):
                try:
                    refuse_unverified((directory / part).read_text(encoding="utf-8") if part != name else text,
                                      f"content/emails/{part}")
                except UnverifiedContent as exc:
                    if strict:
                        raise
                    log.warning("%s", exc)
            m = re.match(r"Betreff:\s*(.+)\nVorschautext:\s*(.+)\n", text)
            if not m:
                raise RuntimeError(f"content/emails/{name}: missing Betreff/Vorschautext lines")
            self.raw[kind] = (m.group(1).strip(), m.group(2).strip(), text[m.end():])

    def render(self, kind: str, to: str, **values) -> Mail:
        subject, preview, body = self.raw[kind]
        md_text = self.env.from_string(body).render(**values).strip() + "\n"
        html_body = markdown.markdown(md_text, extensions=["tables"])
        html = ('<!doctype html><html lang="de"><head><meta charset="utf-8"></head><body style="font-family:system-ui,sans-serif;'
                'color:#17262B;background:#F7F5F0;padding:16px">'
                f'<span style="display:none">{jinja2.utils.markupsafe.escape(preview)}</span>{html_body}</body></html>')
        link = next((values[k] for k in LINK_KEYS if values.get(k)), None)
        return Mail(to=to, subject=subject, preview=preview, text=md_text, html=html, kind=kind, link=link)


class ConsoleMailer:
    """Prints subject + link to stdout. Keeps an in-memory outbox (tests read it). Refused in prod by settings."""
    name = "console"

    def __init__(self):
        self.outbox: list[Mail] = []
        self._lock = threading.Lock()

    def send(self, mail: Mail) -> None:
        with self._lock:
            self.outbox.append(mail)
        print(f"[mailer:console] {mail.kind}: {mail.subject} -> {mail.link or '-'}", file=sys.stdout, flush=True)


class BrevoMailer:
    """Brevo transactional e-mail API. Not called in tests (opener is injectable)."""
    name = "brevo"

    def __init__(self, api_key: str, sender: str, opener=None):
        self._key = api_key
        self.sender = sender
        self._open = opener or urllib.request.urlopen

    def payload(self, mail: Mail) -> dict:
        return {"sender": {"email": self.sender, "name": "Ablaufwerk"}, "to": [{"email": mail.to}],
                "subject": mail.subject, "htmlContent": mail.html, "textContent": mail.text}

    def send(self, mail: Mail) -> None:
        req = urllib.request.Request(BREVO_URL, data=json.dumps(self.payload(mail)).encode(), method="POST",
                                     headers={"api-key": self._key, "content-type": "application/json",
                                              "accept": "application/json"})
        with self._open(req, timeout=15) as resp:  # errors propagate; caller logs the class name only
            if resp.status >= 300:
                raise RuntimeError(f"brevo status {resp.status}")


def make_mailer(settings: Settings):
    if settings.mailer == "brevo":
        return BrevoMailer(settings.brevo_api_key, settings.mail_from)
    return ConsoleMailer()
