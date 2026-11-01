"""Belegbrücke app: FastAPI service with JSON API under /api/v1 (contracts/api.md) and German app pages.

Run offline with defaults:  python -m uvicorn app.main:app --port 8000
"""
from __future__ import annotations

import json
import logging
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

import anyio
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import clock, validation
from .check import detect_format, enforce_known_profile, kind_of, summary_de
from .db import Database
from .helptexts import articles, load_articles
from .jobs import JobRunner
from .mailer import MailTemplates, make_mailer
from .profile import clean, profile_hints, validate_profile
from .security import PRE_COOKIE, SESSION_COOKIE, Security
from .tablecache import read_cached, table_cache
from .settings import (APP_DIR, CHECK_MAX_BYTES, CONSENT_VERSIONS, CURRENT_CONSENT_VERSION, JSON_MAX_BYTES,
                       PLACEHOLDER, SESSION_TTL_SECONDS, TOKEN_TTL_SECONDS, UNSUBSCRIBE_TTL_SECONDS, UPLOAD_MAX_BYTES, brand,
                       load_settings)

log = logging.getLogger("app")

PUBLIC_API = {"/api/v1/check", "/api/v1/subscribe", "/api/v1/events", "/api/v1/confirm", "/api/v1/unsubscribe"}
CORS_API = {"/api/v1/check", "/api/v1/subscribe", "/api/v1/events"}
PRE_SESSION_API = {"/api/v1/auth/magic-link", "/api/v1/auth/callback"}
EMAIL_RE = re.compile(r"^[^\s@<>\"']{1,64}@[^\s@<>\"']{1,190}\.[A-Za-z]{2,}$")
SOURCE_RE = re.compile(r"^(check|guide|ig-[a-z0-9-]{1,20})$")
CODE_RE = re.compile(r"^[a-z0-9-]{1,32}$")
FORMATS = ("xrechnung-cii", "zugferd")
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'")
TRANSFORM_DE = {
    "strip": "Leerzeichen am Rand entfernen",
    "upper": "in Großbuchstaben",
    "de_decimal": "deutsche Zahl (1.234,56) lesen",
    "en_decimal": "englische Zahl (1,234.56) lesen",
    "date_dmy": "Datum TT.MM.JJJJ lesen",
    "date_iso": "Datum JJJJ-MM-TT lesen",
    "abs": "Vorzeichen entfernen (Gutschriften)",
    "gross_to_net": "Bruttopreis in Nettopreis umrechnen",
    "rate_to_category": "Steuersatz in Steuerkategorie umwandeln",
    "unit_map": "Einheit übersetzen (Stk → C62, Std → HUR …)",
    "doc_type": "Belegart erkennen (Rechnung oder Gutschrift)",
}
# Targets without which no invoice can be built; the convert button stays disabled while one is unmapped.
CONVERT_REQUIRED = ["/number", "/issue_date", "/buyer/name", "/lines/*/description", "/lines/*/quantity", "/lines/*/net_price"]
XR_REQUIRED = ["/buyer_reference"]  # BT-10, required for the XRechnung profile (BR-DE-15)
VAT_CATEGORY_CHOICES = [("S", "S – Regelsatz (19 % oder 7 %)"), ("Z", "Z – Nullsatz"), ("E", "E – steuerfrei"),
                        ("AE", "AE – Reverse Charge (Steuerschuld beim Kunden)"), ("K", "K – innergemeinschaftliche Lieferung"),
                        ("G", "G – Ausfuhr"), ("O", "O – nicht steuerbar")]
CONST_CHOICES = {"/lines/*/vat_category": VAT_CATEGORY_CHOICES}
NO_DELIVERY_DATE_DE = ("Kein Leistungsdatum gefunden. Leistungsdatum oder Leistungszeitraum gehören auf jede Rechnung "
                       "(§ 14 Abs. 4 UStG). Wählen Sie eine Spalte oder bestätigen Sie unten „Leistungsdatum = Rechnungsdatum“.")
SOURCE_LABELS = {"check": "über den E-Rechnung-Check", "guide": "über einen Ratgeber-Artikel"}


# ---------------------------------------------------------------------------- logging
class RedactFilter(logging.Filter):
    """Access logs: no client address, no query strings on token paths, no token values anywhere."""
    _tok = re.compile(r"(token=)[^&\s\"]+")
    _token_path = re.compile(r"^(/api/v1/(?:auth/callback|confirm|unsubscribe))\?\S*")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and record.args:
            args = list(record.args)
            if len(args) >= 3 and record.name == "uvicorn.access":
                args[0] = "-"  # client address: raw IPs are never stored
                if isinstance(args[2], str):
                    args[2] = self._token_path.sub(r"\1", args[2])
            record.args = tuple(self._tok.sub(r"\1[redacted]", a) if isinstance(a, str) else a for a in args)
        if isinstance(record.msg, str):
            record.msg = self._tok.sub(r"\1[redacted]", record.msg)
        return True


def _install_log_filter() -> None:
    for name in ("uvicorn.access", "uvicorn.error", "app"):
        lg = logging.getLogger(name)
        if not any(isinstance(f, RedactFilter) for f in lg.filters):
            lg.addFilter(RedactFilter())


# ---------------------------------------------------------------------------- helpers
class ApiError(Exception):
    def __init__(self, status: int, code: str, message_de: str, **extra):
        self.status, self.code, self.message_de, self.extra = status, code, message_de, extra


def err(status: int, code: str, message_de: str, **extra) -> JSONResponse:
    body = {"error": {"code": code, "message_de": message_de, **extra}}
    return JSONResponse(body, status_code=status)


async def read_json(request: Request, limit: int = JSON_MAX_BYTES):
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > limit:
        raise ApiError(413, "too_large", "Die Anfrage ist zu groß.")
    body = await request.body()
    if len(body) > limit:
        raise ApiError(413, "too_large", "Die Anfrage ist zu groß.")
    try:
        data = json.loads(body.decode("utf-8") or "null")
    except (UnicodeDecodeError, ValueError):
        raise ApiError(400, "bad_json", "Die Anfrage enthält kein gültiges JSON.") from None
    if not isinstance(data, dict):
        raise ApiError(400, "bad_json", "Die Anfrage muss ein JSON-Objekt sein.")
    return data


def is_form(request: Request) -> bool:
    return request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded")


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def check_content_length(request: Request, limit: int) -> None:
    cl = request.headers.get("content-length")
    if not cl or not cl.isdigit():
        raise ApiError(411, "length_required", "Die Dateigröße fehlt in der Anfrage.")
    if int(cl) > limit + 64 * 1024:
        raise ApiError(413, "too_large", f"Die Datei ist zu groß (höchstens {limit // (1024 * 1024)} MB).")


def strip_query(path: str) -> str:
    return urlsplit(path).path


# ---------------------------------------------------------------------------- factory
def content_strict(settings) -> bool:
    """Staging/prod refuse to start when a mail or help text still contains `[prüfen` (review H2)."""
    return settings.app_env in ("staging", "prod")


def create_app() -> FastAPI:
    settings = load_settings()
    _install_log_filter()
    db = Database(settings.database_path)
    db.migrate()
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    sec = Security(settings, db)
    strict_content = content_strict(settings)  # refuse unverified "[prüfen" texts where mail is real
    mail_templates = MailTemplates(strict=strict_content)
    load_articles(strict=strict_content)
    mailer = make_mailer(settings)
    runner = JobRunner(settings, db, sec)
    templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
    b = brand()
    # /check: at most this many validations wait in threads at once; the shared semaphore caps the JVMs.
    check_limiter = anyio.CapacityLimiter(4)

    def send_welcome2_due() -> None:
        due = db.all("SELECT email FROM subscribers WHERE confirmed_at IS NOT NULL AND confirmed_at<? AND welcome2_sent_at IS NULL",
                     (clock.now() - 3 * 86400,))
        for row in due:
            send_mail("welcome2", row["email"], app_url=f"{settings.app_public_url}/login",
                      unsubscribe_url=unsubscribe_url(row["email"]))
            db.execute("UPDATE subscribers SET welcome2_sent_at=? WHERE email=?", (clock.now(), row["email"]))

    @asynccontextmanager
    async def lifespan(_app):
        n = runner.recover()
        if n:
            log.warning("marked %d interrupted jobs as failed", n)
        if settings.secret_was_generated and settings.app_env == "dev":
            log.warning("SESSION_SECRET not set: using a random secret (sessions end on restart)")
        if settings.app_env != "test":
            runner.purge()
            runner.start_timer(tick=send_welcome2_due)
        yield
        runner.shutdown()

    app = FastAPI(title=b["product"], lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings, app.state.db, app.state.security = settings, db, sec
    app.state.mailer, app.state.runner, app.state.send_welcome2_due = mailer, runner, send_welcome2_due
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    # ------------------------------------------------------------------ mail
    def send_mail(kind: str, to: str, **values) -> None:
        site = settings.site_public_url
        values.setdefault("site_url", site)
        values.setdefault("check_url", f"{site}/e-rechnung-pruefen/")
        values.setdefault("app_url", f"{settings.app_public_url}/login")
        mail = mail_templates.render(kind, to, **values)
        try:
            mailer.send(mail)
        except Exception as exc:
            log.error("mail not sent: %s", type(exc).__name__)

    def unsubscribe_url(email: str) -> str:
        tok = sec.issue_token("unsubscribe", email, ttl=UNSUBSCRIBE_TTL_SECONDS)
        return f"{settings.app_public_url}/api/v1/unsubscribe?{urlencode({'token': tok})}"

    # ------------------------------------------------------------------ middleware
    @app.middleware("http")
    async def guard(request: Request, call_next):
        path = request.url.path
        origin = request.headers.get("origin")
        method = request.method
        is_api = path.startswith("/api/")
        try:
            resp = await _route(request, path, origin, method, is_api, call_next)
        except Exception as exc:  # unexpected: log the class name only, never values or tracebacks
            log.error("unhandled error: %s", type(exc).__name__)
            if is_api:
                resp = err(500, "internal_error", "Interner Fehler. Bitte versuchen Sie es erneut.")
            else:
                resp = HTMLResponse("<!doctype html><html lang=\"de\"><meta charset=\"utf-8\"><title>Fehler</title>"
                                    "<p>Interner Fehler. Bitte laden Sie die Seite neu.</p></html>", status_code=500)
        cors_ok = path in CORS_API and origin and origin.rstrip("/").lower() == settings.site_origin
        if cors_ok:
            resp.headers["Access-Control-Allow-Origin"] = settings.site_origin
            resp.headers["Vary"] = "Origin"
        h = resp.headers
        h["Content-Security-Policy"] = CSP
        h["X-Frame-Options"] = "DENY"
        h["X-Content-Type-Options"] = "nosniff"
        # Default same-origin, not no-referrer: under no-referrer browsers send Origin: null on form POSTs and our own
        # same-origin check rejects them. Token links set no-referrer on their redirect only (see token_page).
        if "referrer-policy" not in h:
            h["Referrer-Policy"] = "same-origin"
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        if settings.secure_cookies:
            h["Strict-Transport-Security"] = "max-age=31536000"
        if not settings.is_prod:
            h["X-Robots-Tag"] = "noindex, nofollow"
        if not path.startswith("/static/"):
            h.setdefault("Cache-Control", "no-store")
        return resp

    async def _route(request: Request, path, origin, method, is_api, call_next):
        cors_ok = path in CORS_API and origin and origin.rstrip("/").lower() == settings.site_origin
        if method == "OPTIONS":
            if path in CORS_API and cors_ok:
                resp = Response(status_code=204)
                resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
                resp.headers["Access-Control-Max-Age"] = "600"
            elif path in CORS_API:
                resp = err(403, "origin_not_allowed", "Diese Herkunft ist nicht erlaubt.")
            else:
                resp = err(405, "method_not_allowed", "Diese Methode ist nicht erlaubt.")
        elif is_api and method not in ("GET", "HEAD"):
            if path in PUBLIC_API:
                allowed = {settings.site_origin, settings.app_origin}
                if origin and origin.rstrip("/").lower() not in allowed:
                    resp = err(403, "origin_not_allowed", "Diese Herkunft ist nicht erlaubt.")
                else:
                    resp = await call_next(request)
            elif not sec.same_origin(request.headers):
                resp = err(403, "origin_mismatch", "Anfrage von fremder Seite abgelehnt.")
            else:
                resp = await call_next(request)
        else:
            resp = await call_next(request)
        return resp

    # ------------------------------------------------------------------ errors
    @app.exception_handler(ApiError)
    async def api_error(_request, exc: ApiError):
        return err(exc.status, exc.code, exc.message_de, **exc.extra)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, _exc):
        return err(422, "invalid_request", "Die Anfrage ist unvollständig oder ungültig.")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/api/"):
            msgs = {404: ("not_found", "Nicht gefunden."), 405: ("method_not_allowed", "Diese Methode ist nicht erlaubt.")}
            code, msg = msgs.get(exc.status_code, ("error", "Die Anfrage konnte nicht bearbeitet werden."))
            return err(exc.status_code, code, msg)
        return page(request, "message.html", {"title": "Seite nicht gefunden",
                                              "text": "Diese Seite gibt es nicht. Prüfen Sie die Adresse."}, status=exc.status_code)

    # ------------------------------------------------------------------ auth helpers
    def current(request: Request):
        return sec.session(request.cookies.get(SESSION_COOKIE))

    async def csrf_ok(request: Request, expected: str | None) -> bool:
        token = request.headers.get("x-csrf-token")
        if not token and is_form(request):
            form = await request.form()
            token = form.get("csrf_token")
        return sec.equal(token, expected)

    async def require_user(request: Request):
        """Session + CSRF header for state-changing app endpoints (origin is checked in the middleware)."""
        sess = current(request)
        if not sess:
            raise ApiError(401, "not_logged_in", "Bitte melden Sie sich an.")
        if request.method not in ("GET", "HEAD") and not await csrf_ok(request, sess["csrf_token"]):
            raise ApiError(403, "csrf", "Sicherheitsprüfung fehlgeschlagen. Bitte laden Sie die Seite neu.")
        return sess

    async def require_pre_csrf(request: Request) -> None:
        if not await csrf_ok(request, sec.pre_csrf(request.cookies.get(PRE_COOKIE))):
            raise ApiError(403, "csrf", "Sicherheitsprüfung fehlgeschlagen. Bitte laden Sie die Seite neu.")

    def ensure_pre(request: Request) -> tuple[str, bool]:
        pre = request.cookies.get(PRE_COOKIE)
        if pre and len(pre) <= 200:
            return pre, False
        return secrets.token_urlsafe(24), True

    def set_cookie(resp: Response, name: str, value: str, max_age: int) -> None:
        resp.set_cookie(name, value, max_age=max_age, httponly=True, secure=settings.secure_cookies, samesite="lax", path="/")

    # ------------------------------------------------------------------ page rendering
    def page(request: Request, name: str, ctx: dict | None = None, status: int = 200, sess=None, pre: str | None = None):
        sess = sess if sess is not None else current(request)
        csrf = sess["csrf_token"] if sess else (sec.pre_csrf(pre) if pre else None)
        context = {"brand": b, "scope_line": b["scope_line"], "staging": settings.show_staging_banner,
                   "user": sess, "csrf": csrf, "help_articles": list(articles().values()),
                   "placeholder": PLACEHOLDER, "site_url": settings.site_public_url}
        context.update(ctx or {})
        return templates.TemplateResponse(request, name, context, status_code=status)

    def login_redirect():
        return RedirectResponse("/login", status_code=303)

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        return {"status": "ok"}

    # ================================================================== PUBLIC API
    @app.post("/api/v1/check")
    async def check(request: Request):
        import engine
        if sec.rate_limited("check:" + sec.ip_hash(client_ip(request)), 20):
            raise ApiError(429, "rate_limited", "Zu viele Prüfungen. Bitte warten Sie eine Stunde (höchstens 20 pro Stunde).")
        check_content_length(request, CHECK_MAX_BYTES)
        form = await request.form(max_files=1, max_fields=5)
        f = form.get("file")
        if f is None or isinstance(f, str):
            raise ApiError(400, "file_missing", "Bitte wählen Sie eine Datei aus.")
        data = await f.read(CHECK_MAX_BYTES + 1)
        await form.close()
        if len(data) > CHECK_MAX_BYTES:
            raise ApiError(413, "too_large", "Die Datei ist zu groß (höchstens 5 MB).")
        if not data:
            raise ApiError(400, "file_empty", "Die Datei ist leer.")
        kind = kind_of(data, f.filename or "")
        if kind is None:
            raise ApiError(415, "unsupported_type", "Bitte laden Sie eine XML- oder PDF-Datei hoch.")
        fname = f.filename or f"datei.{kind}"

        def run_check():
            rep = validation.validate_one(data, fname, engine)
            return rep, detect_format(data, kind, rep)

        report, fmt = await anyio.to_thread.run_sync(run_check, limiter=check_limiter)
        del data  # discarded after the call
        enforce_known_profile(report, fmt)
        report["format"] = fmt
        report["summary_de"] = summary_de(report, fmt)
        return report

    @app.post("/api/v1/subscribe")
    async def subscribe(request: Request):
        body = await read_json(request, 16 * 1024)
        email = str(body.get("email") or "").strip()
        if len(email) > 254 or not EMAIL_RE.match(email):
            raise ApiError(400, "invalid_email", "Bitte geben Sie eine gültige E-Mail-Adresse ein.")
        if body.get("consent") is not True:
            raise ApiError(400, "consent_missing", "Bitte bestätigen Sie die Einwilligung.")
        version = body.get("consent_version") or CURRENT_CONSENT_VERSION
        if version not in CONSENT_VERSIONS:
            raise ApiError(400, "unknown_consent_version", "Diese Version des Einwilligungstexts ist unbekannt. Bitte laden Sie die Seite neu.")
        source = body.get("source")
        if source is not None and (not isinstance(source, str) or not SOURCE_RE.match(source)):
            raise ApiError(400, "invalid_source", "Ungültige Herkunftsangabe.")
        if sec.rate_limited("subscribe-ip:" + sec.ip_hash(client_ip(request)), 10):
            raise ApiError(429, "rate_limited", "Zu viele Anmeldungen von dieser Verbindung. Bitte versuchen Sie es später erneut.")
        email_l = email.lower()
        accepted = {"status": "pending", "message_de": "Bitte bestätigen Sie die Anmeldung über den Link in der E-Mail."}
        if sec.rate_limited("subscribe-email:" + sec.email_hash(email_l), 3):
            return JSONResponse(accepted, status_code=202)  # silent: no enumeration
        row = db.one("SELECT confirmed_at FROM subscribers WHERE email=?", (email_l,))
        if row and row["confirmed_at"]:
            return JSONResponse(accepted, status_code=202)
        now = clock.now()
        db.execute("INSERT INTO subscribers (email, consent_version, source, requested_at) VALUES (?,?,?,?) "
                   "ON CONFLICT(email) DO UPDATE SET consent_version=excluded.consent_version, source=excluded.source, "
                   "requested_at=excluded.requested_at", (email_l, version, source, now))
        tok = sec.issue_token("optin", email_l)
        label = SOURCE_LABELS.get(source or "", "über Instagram" if (source or "").startswith("ig-") else "auf unserer Website")
        send_mail("optin", email_l, confirm_url=f"{settings.app_public_url}/api/v1/confirm?{urlencode({'token': tok})}",
                  source_label=label, requested_at=clock.de_datetime(now))
        db.execute("INSERT INTO events (name, path, code, created_at) VALUES ('subscribe', '/api/v1/subscribe', ?, ?)",
                   (source if source and source.startswith("ig-") else None, now))
        return JSONResponse(accepted, status_code=202)

    def token_cookie(purpose: str) -> str:
        return f"bb_t_{purpose}"

    def token_page(request: Request, purpose: str, title: str, text: str, button: str, action: str, status=200):
        """Token links (review M2): GET with ?token= only moves the token into a short-lived HttpOnly cookie
        limited to this path and redirects to the same path without the query (that redirect carries
        Referrer-Policy: no-referrer). The confirm page itself has no token in its URL, so neither its
        subresources nor its form POST can leak the token via Referer, and it keeps the same-origin policy
        (no-referrer on the page would make browsers send Origin: null on the POST)."""
        q = request.query_params.get("token")
        if q is not None:
            resp = RedirectResponse(action, status_code=303)
            resp.headers["Referrer-Policy"] = "no-referrer"
            if 0 < len(q) <= 200:
                resp.set_cookie(token_cookie(purpose), q, max_age=TOKEN_TTL_SECONDS if purpose != "unsubscribe" else 3600,
                                httponly=True, secure=settings.secure_cookies, samesite="lax", path=action)
            return resp
        tok = request.cookies.get(token_cookie(purpose))
        if not sec.peek_token(purpose, tok):
            return page(request, "message.html", {"title": "Link ungültig oder abgelaufen",
                                                  "text": "Dieser Link ist abgelaufen oder wurde schon benutzt. "
                                                          "Links gelten 15 Minuten und nur einmal."}, status=400)
        pre, new = ensure_pre(request)
        resp = page(request, "token_confirm.html", {"title": title, "text": text, "button": button,
                                                    "action": action}, status=status, pre=pre)
        resp.headers["Referrer-Policy"] = "same-origin"
        if new:
            set_cookie(resp, PRE_COOKIE, pre, 3600)
        return resp

    async def form_token(request: Request, purpose: str) -> str | None:
        if is_form(request):
            form = await request.form()
            t = form.get("token")
            if isinstance(t, str) and t:
                return t
        return request.cookies.get(token_cookie(purpose)) or request.query_params.get("token")

    def clear_token_cookie(resp: Response, purpose: str, action: str) -> Response:
        resp.delete_cookie(token_cookie(purpose), path=action)
        return resp

    @app.get("/api/v1/confirm", response_class=HTMLResponse)
    async def confirm_get(request: Request):
        return token_page(request, "optin", "Anmeldung bestätigen",
                          "Bitte bestätigen Sie, dass Sie E-Mails von Ablaufwerk erhalten möchten.",
                          "Anmeldung bestätigen", "/api/v1/confirm")

    @app.post("/api/v1/confirm")
    async def confirm_post(request: Request):
        email = sec.consume_token("optin", await form_token(request, "optin"))
        if not email:
            return page(request, "message.html", {"title": "Link ungültig oder abgelaufen",
                                                  "text": "Bitte melden Sie sich erneut an."}, status=400)
        now = clock.now()
        n = db.execute("UPDATE subscribers SET confirmed_at=?, unsubscribed_at=NULL WHERE email=?", (now, email))
        if n:
            send_mail("welcome1", email, unsubscribe_url=unsubscribe_url(email))
        return clear_token_cookie(RedirectResponse("/bestaetigt", status_code=303), "optin", "/api/v1/confirm")

    @app.get("/api/v1/unsubscribe", response_class=HTMLResponse)
    async def unsubscribe_get(request: Request):
        return token_page(request, "unsubscribe", "Abmelden",
                          "Möchten Sie keine E-Mails von Ablaufwerk mehr erhalten?", "Jetzt abmelden", "/api/v1/unsubscribe")

    @app.post("/api/v1/unsubscribe")
    async def unsubscribe_post(request: Request):
        email = sec.consume_token("unsubscribe", await form_token(request, "unsubscribe"))
        if not email:
            return page(request, "message.html", {"title": "Link ungültig oder abgelaufen",
                                                  "text": "Dieser Abmeldelink ist nicht mehr gültig. Antworten Sie einfach "
                                                          "auf eine unserer E-Mails mit „abmelden“."}, status=400)
        now = clock.now()
        with db.tx() as conn:
            sub = conn.execute("SELECT consent_version, requested_at, confirmed_at FROM subscribers WHERE email=?",
                               (email,)).fetchone()
            if sub:  # proof of consent for mails already sent (Art. 7(1) DSGVO): HMAC of the address, no address
                conn.execute("INSERT INTO consent_records (email_hmac, consent_version, requested_at, confirmed_at, unsubscribed_at) "
                             "VALUES (?,?,?,?,?)", (sec.consent_hmac(email), sub["consent_version"], sub["requested_at"],
                                                    sub["confirmed_at"], now))
            conn.execute("DELETE FROM subscribers WHERE email=?", (email,))
            conn.execute("DELETE FROM tokens WHERE email=? AND purpose IN ('optin','unsubscribe')", (email,))
        resp = page(request, "message.html", {"title": "Sie sind abgemeldet",
                                              "text": "Ihre Adresse wurde gelöscht. Als Nachweis der früheren Einwilligung "
                                                      "behalten wir nur einen nicht umkehrbaren Prüfwert der Adresse mit "
                                                      "Version und Datum."})
        return clear_token_cookie(resp, "unsubscribe", "/api/v1/unsubscribe")

    @app.post("/api/v1/events")
    async def events(request: Request):
        body = await read_json(request, 2048)
        name = body.get("name")
        if not isinstance(name, str) or name not in settings.events_allowed:
            raise ApiError(400, "unknown_event", "Unbekanntes Ereignis.")
        path = body.get("path")
        if path is not None and (not isinstance(path, str) or not path.startswith("/")):
            raise ApiError(400, "invalid_path", "Ungültiger Pfad.")
        code = body.get("code")
        if code is not None and (not isinstance(code, str) or not CODE_RE.match(code)):
            raise ApiError(400, "invalid_code", "Ungültiger Code.")
        if sec.rate_limited("events:" + sec.ip_hash(client_ip(request)), 600):
            raise ApiError(429, "rate_limited", "Zu viele Ereignisse.")
        db.execute("INSERT INTO events (name, path, code, created_at) VALUES (?,?,?,?)",
                   (name, strip_query(path)[:200] if path else None, code, clock.now()))
        return Response(status_code=204)

    # ================================================================== AUTH
    @app.post("/api/v1/auth/magic-link")
    async def magic_link(request: Request):
        await require_pre_csrf(request)
        if is_form(request):
            email = str((await request.form()).get("email") or "").strip()
        else:
            email = str((await read_json(request, 4096)).get("email") or "").strip()
        if len(email) > 254 or not EMAIL_RE.match(email):
            raise ApiError(400, "invalid_email", "Bitte geben Sie eine gültige E-Mail-Adresse ein.")
        email_l = email.lower()
        if sec.rate_limited("magic-ip:" + sec.ip_hash(client_ip(request)), 20) or \
                sec.rate_limited("magic-email:" + sec.email_hash(email_l), 5):
            raise ApiError(429, "rate_limited", "Zu viele Anmeldelinks angefordert. Bitte warten Sie eine Stunde.")
        tok = sec.issue_token("login", email_l)
        send_mail("login", email_l, login_url=f"{settings.app_public_url}/api/v1/auth/callback?{urlencode({'token': tok})}",
                  requested_at=clock.de_datetime(clock.now()))
        if is_form(request):
            return RedirectResponse("/login?gesendet=1", status_code=303)
        return JSONResponse({"status": "sent", "message_de": "Wir haben Ihnen einen Anmeldelink geschickt. Er gilt 15 Minuten."},
                            status_code=202)

    @app.get("/api/v1/auth/callback", response_class=HTMLResponse)
    async def callback_get(request: Request):
        return token_page(request, "login", "Anmelden", "Klicken Sie auf den Knopf, um sich bei Belegbrücke anzumelden.",
                          "Jetzt anmelden", "/api/v1/auth/callback")

    @app.post("/api/v1/auth/callback")
    async def callback_post(request: Request):
        await require_pre_csrf(request)
        email = sec.consume_token("login", await form_token(request, "login"))
        if not email:
            return page(request, "message.html", {"title": "Link ungültig oder abgelaufen",
                                                  "text": "Bitte fordern Sie einen neuen Anmeldelink an."}, status=400)
        now = clock.now()
        with db.tx() as conn:
            row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if row:
                uid = row["id"]
                conn.execute("UPDATE users SET last_login_at=? WHERE id=?", (now, uid))
            else:
                uid = Security.new_id()
                conn.execute("INSERT INTO users (id, email, plan, created_at, last_login_at) VALUES (?,?,?,?,?)",
                             (uid, email, "free", now, now))
        raw = sec.create_session(uid)
        resp = RedirectResponse("/app", status_code=303)
        set_cookie(resp, SESSION_COOKIE, raw, SESSION_TTL_SECONDS)
        resp.delete_cookie(PRE_COOKIE, path="/")
        return clear_token_cookie(resp, "login", "/api/v1/auth/callback")

    @app.post("/api/v1/auth/logout")
    async def logout(request: Request):
        await require_user(request)
        sec.end_session(request.cookies.get(SESSION_COOKIE))
        resp = RedirectResponse("/login", status_code=303) if is_form(request) else JSONResponse({"status": "logged_out"})
        resp.delete_cookie(SESSION_COOKIE, path="/")
        return resp

    # ================================================================== APP API
    def own_upload(user_id: str, upload_id) -> dict:
        row = db.one("SELECT * FROM uploads WHERE id=? AND user_id=?", (str(upload_id), user_id))
        if not row:
            raise ApiError(404, "upload_not_found", "Upload nicht gefunden.")
        return dict(row)

    def require_raw(upload: dict) -> Path:
        if not upload["path"] or not Path(upload["path"]).exists():
            raise ApiError(410, "upload_deleted", "Die hochgeladene Datei wurde bereits gelöscht (nach der Umwandlung oder "
                                                  "nach 24 Stunden). Bitte laden Sie sie erneut hoch.")
        return Path(upload["path"])

    def get_profile(user_id: str) -> dict | None:
        row = db.one("SELECT profile_json FROM seller_profiles WHERE user_id=?", (user_id,))
        return json.loads(row["profile_json"]) if row else None

    def unreadable(exc) -> ApiError:
        return ApiError(400, "unreadable_file", getattr(exc, "message_de", None) or "Die Datei konnte nicht gelesen werden.")

    async def read_upload_table(upload: dict):
        """Parsed table of an upload, parsed at most once (cache) and always off the event loop."""
        import mapping
        path = require_raw(upload)
        try:
            return await run_in_threadpool(read_cached, upload["id"], path, upload["filename"] or f"upload.{upload['ext']}")
        except mapping.TableReadError as exc:
            raise unreadable(exc) from None

    def column_samples(table) -> dict:
        samples = {}
        for i, c in enumerate(table.columns):
            samples[c] = next((r[i] for r in table.rows[:20] if i < len(r) and r[i].strip()), "")[:60]
        return samples

    @app.post("/api/v1/uploads", status_code=201)
    async def uploads(request: Request):
        import mapping
        sess = await require_user(request)
        check_content_length(request, UPLOAD_MAX_BYTES)
        if sec.rate_limited("upload:" + sess["user_id"], 60):
            raise ApiError(429, "rate_limited", "Zu viele Uploads. Bitte warten Sie etwas.")
        form = await request.form(max_files=1, max_fields=5)
        f = form.get("file")
        if f is None or isinstance(f, str):
            raise ApiError(400, "file_missing", "Bitte wählen Sie eine Datei aus.")
        name = (f.filename or "").strip()[-120:]
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        data = await f.read(UPLOAD_MAX_BYTES + 1)
        await form.close()
        if ext == "xls":
            raise ApiError(415, "unsupported_type", "Das alte Excel-Format .xls wird nicht unterstützt. Bitte speichern Sie die Datei als .xlsx oder CSV.")
        if ext not in ("csv", "xlsx"):
            raise ApiError(415, "unsupported_type", "Bitte laden Sie eine CSV- oder XLSX-Datei hoch.")
        if len(data) > UPLOAD_MAX_BYTES:
            raise ApiError(413, "too_large", "Die Datei ist zu groß (höchstens 10 MB).")
        if not data:
            raise ApiError(400, "file_empty", "Die Datei ist leer.")
        try:
            table = await run_in_threadpool(mapping.read_table, data, name)
        except mapping.TableReadError as exc:
            raise unreadable(exc) from None
        uid = Security.new_id()
        runner.upload_dir.mkdir(parents=True, exist_ok=True)
        path = runner.upload_dir / f"{uid}.{ext}"
        path.write_bytes(data)
        db.execute("INSERT INTO uploads (id, user_id, filename, ext, size, row_count, columns_json, samples_json, path, created_at) "
                   "VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (uid, sess["user_id"], name, ext, len(data), len(table.rows), json.dumps(table.columns, ensure_ascii=False),
                    json.dumps(column_samples(table), ensure_ascii=False), str(path), clock.now()))
        table_cache.put(uid, table)
        db.execute("INSERT INTO events (name, path, code, created_at) VALUES ('upload', '/app/upload', NULL, ?)", (clock.now(),))
        return {"upload_id": uid, "columns": table.columns, "sample_rows": table.rows[:5], "row_count": len(table.rows)}

    def find_reusable(user_id: str, columns: list[str]) -> dict | None:
        for row in db.all("SELECT mapping_json, updated_at FROM mappings WHERE user_id=? AND save_for_reuse=1 AND confirmed=1 "
                          "ORDER BY updated_at DESC LIMIT 20", (user_id,)):
            m = json.loads(row["mapping_json"])
            cols = {f["source_column"] for f in m["fields"] if f.get("source_column")}
            gcol = m.get("grouping", {}).get("invoice_number_column")
            if cols <= set(columns) and (gcol is None or gcol in columns):
                return m
        return None

    def store_mapping(user_id: str, upload_id: str, m: dict, columns: list[str]) -> dict:
        mid = Security.new_id()
        m = dict(m, mapping_id=mid, version=1)
        now = clock.now()
        db.execute("INSERT INTO mappings (id, user_id, upload_id, provider, model, mapping_json, columns_json, created_at, updated_at) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (mid, user_id, upload_id, m.get("provider", "heuristic"), m.get("model"),
                    json.dumps(m, ensure_ascii=False), json.dumps(columns, ensure_ascii=False), now, now))
        return m

    @app.post("/api/v1/mappings/propose")
    async def propose(request: Request):
        import mapping
        sess = await require_user(request)
        body = await read_json(request)
        upload = own_upload(sess["user_id"], body.get("upload_id"))
        table = await read_upload_table(upload)
        reused = find_reusable(sess["user_id"], table.columns) if not body.get("ignore_saved") else None
        if reused:
            m = {k: reused[k] for k in ("provider", "model", "grouping", "fields") if k in reused}
        else:
            profile = get_profile(sess["user_id"]) or {"seller": {}, "payment_defaults": {}, "defaults": {}}
            provider = settings.ai_provider if settings.ai_provider in ("heuristic", "anthropic") else "heuristic"
            real = body.get("send_real_values") is True
            try:
                m = await run_in_threadpool(lambda: mapping.propose(table, profile, provider=provider, send_real_values=real))
            except mapping.TableReadError as exc:
                raise unreadable(exc) from None
        m = store_mapping(sess["user_id"], upload["id"], m, table.columns)
        return dict(m, reused=bool(reused))

    def bad_type(msg: str) -> ApiError:
        return ApiError(400, "invalid_mapping", "Die Zuordnung ist ungültig: " + msg)

    def normalise_fields(fields) -> list[dict]:
        if not isinstance(fields, list) or len(fields) > 100:
            raise ApiError(422, "invalid_mapping", "Die Zuordnung ist ungültig: fields fehlt.")
        out = []
        for i, f in enumerate(fields, 1):
            if not isinstance(f, dict):
                raise bad_type(f"Feld {i} ist kein Objekt.")
            if not isinstance(f.get("target"), str) or len(f["target"]) > 100:
                raise bad_type(f"Feld {i}: „target“ muss Text sein.")
            if f.get("source_column") is not None and (not isinstance(f["source_column"], str) or len(f["source_column"]) > 300):
                raise bad_type(f"Feld {i}: „source_column“ muss Text sein.")
            tr = f.get("transform")
            if tr is not None and (not isinstance(tr, list) or len(tr) > 10 or not all(isinstance(x, str) for x in tr)):
                raise bad_type(f"Feld {i}: „transform“ muss eine Liste von Texten sein.")
            if f.get("reason_de") is not None and not isinstance(f["reason_de"], str):
                raise bad_type(f"Feld {i}: „reason_de“ muss Text sein.")
            item = {"target": f.get("target")}
            if f.get("source_column") is not None:
                item["source_column"] = f["source_column"]
            if f.get("constant") is not None:
                if not isinstance(f["constant"], str) or len(f["constant"]) > 300:
                    raise ApiError(422, "invalid_mapping", "Ein fester Wert ist zu lang.")
                item["constant"] = f["constant"]
            item["transform"] = f.get("transform") or []
            conf = f.get("confidence", 1.0)
            item["confidence"] = conf if isinstance(conf, (int, float)) and 0 <= conf <= 1 else 1.0
            reason = f.get("reason_de")
            item["reason_de"] = reason[:300] if isinstance(reason, str) else "Von Ihnen festgelegt"
            out.append(item)
        return out

    @app.put("/api/v1/mappings/{mapping_id}")
    async def put_mapping(mapping_id: str, request: Request):
        import mapping
        sess = await require_user(request)
        row = db.one("SELECT * FROM mappings WHERE id=? AND user_id=?", (mapping_id, sess["user_id"]))
        if not row:
            raise ApiError(404, "mapping_not_found", "Zuordnung nicht gefunden.")
        body = await read_json(request)
        old = json.loads(row["mapping_json"])
        grouping = body.get("grouping", old.get("grouping"))
        if not isinstance(grouping, dict):
            raise ApiError(422, "invalid_mapping", "Die Zuordnung ist ungültig: grouping fehlt.")
        grouping = {"mode": grouping.get("mode"), "invoice_number_column": grouping.get("invoice_number_column")}
        if not isinstance(grouping["mode"], (str, type(None))) or not isinstance(grouping["invoice_number_column"], (str, type(None))):
            raise bad_type("„grouping“ enthält keinen Text.")
        new = {"mapping_id": mapping_id, "version": 1, "provider": old.get("provider", "heuristic"),
               "grouping": grouping, "fields": normalise_fields(body.get("fields", old.get("fields")))}
        if old.get("model"):
            new["model"] = old["model"]
        columns = json.loads(row["columns_json"])
        problems = mapping.validate_mapping(new, columns)
        if problems:
            raise ApiError(422, "invalid_mapping", "Die Zuordnung ist ungültig: " + "; ".join(problems[:5]), problems=problems)
        reuse = 1 if body.get("save_for_reuse") is True else 0
        db.execute("UPDATE mappings SET mapping_json=?, save_for_reuse=?, confirmed=1, updated_at=? WHERE id=?",
                   (json.dumps(new, ensure_ascii=False), reuse, clock.now(), mapping_id))
        db.execute("INSERT INTO events (name, path, code, created_at) VALUES ('mapping_confirmed', '/app/mapping', NULL, ?)", (clock.now(),))
        return dict(new, save_for_reuse=bool(reuse))

    @app.post("/api/v1/conversions", status_code=202)
    async def conversions(request: Request):
        import mapping
        sess = await require_user(request)
        body = await read_json(request)
        profile = get_profile(sess["user_id"])
        if not profile:
            raise ApiError(409, "profile_missing", "Bitte legen Sie zuerst Ihr Unternehmensprofil an.")
        upload = own_upload(sess["user_id"], body.get("upload_id"))
        require_raw(upload)
        mrow = db.one("SELECT * FROM mappings WHERE id=? AND user_id=?", (str(body.get("mapping_id")), sess["user_id"]))
        if not mrow:
            raise ApiError(404, "mapping_not_found", "Zuordnung nicht gefunden.")
        formats = body.get("formats") or ["xrechnung-cii"]
        if not isinstance(formats, list) or not formats or any(f not in FORMATS for f in formats):
            raise ApiError(422, "invalid_formats", "Unbekanntes Format. Erlaubt: xrechnung-cii, zugferd.")
        prof = body.get("profile") or profile.get("defaults", {}).get("profile", "xrechnung")
        if prof not in ("xrechnung", "zugferd"):
            raise ApiError(422, "invalid_profile", "Unbekanntes Profil. Erlaubt: xrechnung, zugferd.")
        problems = mapping.validate_mapping(json.loads(mrow["mapping_json"]), json.loads(upload["columns_json"]))
        if problems:
            raise ApiError(422, "invalid_mapping", "Die Zuordnung passt nicht zu dieser Datei: " + "; ".join(problems[:5]))
        # Jobs older than an hour that never finished do not block new ones (crash/restart, see JobRunner.recover).
        active = db.one("SELECT COUNT(*) AS n FROM jobs WHERE user_id=? AND status IN ('queued','running') AND created_at>?",
                        (sess["user_id"], clock.now() - 3600))["n"]
        if active >= 3:
            raise ApiError(429, "too_many_jobs", "Es laufen bereits mehrere Umwandlungen. Bitte warten Sie, bis sie fertig sind.")
        jid = Security.new_id()
        db.execute("INSERT INTO jobs (id, user_id, upload_id, mapping_id, formats, profile, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
                   (jid, sess["user_id"], upload["id"], mrow["id"], json.dumps(sorted(set(formats))), prof, "queued", clock.now()))
        runner.submit(jid)
        return {"job_id": jid, "status": "queued"}

    def job_view(job) -> dict:
        expires = job["created_at"] + settings.retention_seconds
        status = job["status"]
        if status != "expired" and clock.now() >= expires and status not in ("queued", "running"):
            runner.purge()
            job = db.one("SELECT * FROM jobs WHERE id=?", (job["id"],))
            status = job["status"]
        out = {"job_id": job["id"], "status": status, "profile": job["profile"], "formats": json.loads(job["formats"]),
               "created_at": clock.iso(job["created_at"]), "expires_at": clock.iso(expires),
               "expires_de": clock.de_long(expires), "mapping_id": job["mapping_id"], "upload_available": False,
               "invoices": [], "row_errors": [], "zip_url": None, "formats_unavailable": [],
               "summary": {"invoices": job["invoice_count"], "valid": job["valid_count"]}}
        if status == "expired":
            out["message_de"] = "Dieser Auftrag ist abgelaufen. Dateien und Fehlermeldungen wurden nach 24 Stunden gelöscht."
        elif status == "failed":
            out["error"] = {"code": "conversion_failed", "message_de": job["error_de"] or "Die Umwandlung ist fehlgeschlagen."}
        elif status == "done" and job["result_json"]:
            res = json.loads(job["result_json"])
            out["invoices"] = res["invoices"]
            out["row_errors"] = res["row_errors"]
            out["formats_unavailable"] = res.get("formats_unavailable", [])
            if res.get("zip_file_id"):
                out["zip_url"] = f"/api/v1/files/{res['zip_file_id']}"
            out["summary"]["offered"] = sum(1 for i in res["invoices"] if i.get("counted"))
            up = db.one("SELECT path FROM uploads WHERE id=?", (job["upload_id"],))
            out["upload_available"] = bool(up and up["path"] and Path(up["path"]).exists())
            out["summary"]["limit_reached"] = any(i.get("limit_reached") for i in res["invoices"])
            if not res.get("zip_file_id"):  # why nothing was offered: monthly limit vs. no valid invoice
                out["summary"]["no_offer_reason"] = "limit" if out["summary"]["limit_reached"] else "invalid"
        return out

    @app.get("/api/v1/conversions/{job_id}")
    async def conversion_status(job_id: str, request: Request):
        sess = await require_user(request)
        job = db.one("SELECT * FROM jobs WHERE id=? AND user_id=?", (job_id, sess["user_id"]))
        if not job:
            raise ApiError(404, "job_not_found", "Auftrag nicht gefunden.")
        return job_view(job)

    @app.get("/api/v1/files/{file_id}")
    async def files(file_id: str, request: Request):
        sess = await require_user(request)
        row = db.one("SELECT * FROM files WHERE id=? AND user_id=?", (file_id, sess["user_id"]))
        gone = ApiError(404, "file_not_found", "Die Datei ist nicht (mehr) verfügbar. Erzeugte Dateien werden nach 24 Stunden gelöscht.")
        if not row or row["deleted_at"] or not row["path"]:
            raise gone
        if clock.now() >= row["created_at"] + settings.retention_seconds:
            runner.purge()
            raise gone
        p = Path(row["path"])
        if not p.exists():
            raise gone
        return FileResponse(p, media_type=row["media_type"], filename=row["filename"],
                            headers={"Cache-Control": "no-store"})

    @app.get("/api/v1/seller-profile")
    async def get_seller_profile(request: Request):
        sess = await require_user(request)
        prof = get_profile(sess["user_id"])
        if not prof:
            raise ApiError(404, "profile_missing", "Es ist noch kein Unternehmensprofil angelegt.")
        return prof

    @app.put("/api/v1/seller-profile")
    async def put_seller_profile(request: Request):
        sess = await require_user(request)
        prof = clean(await read_json(request))
        prof.setdefault("payment_defaults", {})
        prof.setdefault("seller", {})
        problems = validate_profile(prof)
        if problems:
            raise ApiError(422, "invalid_profile", "Bitte prüfen Sie die markierten Angaben.", fields=problems)
        db.execute("INSERT INTO seller_profiles (user_id, profile_json, updated_at) VALUES (?,?,?) "
                   "ON CONFLICT(user_id) DO UPDATE SET profile_json=excluded.profile_json, updated_at=excluded.updated_at",
                   (sess["user_id"], json.dumps(prof, ensure_ascii=False), clock.now()))
        return dict(prof, hints_de=profile_hints(prof))

    def usage_view(sess) -> dict:
        used = runner.used(sess["user_id"])
        limit = runner.plan_limit(sess["plan"])
        return {"month": clock.month_key(), "plan": sess["plan"], "used": used, "limit": limit, "remaining": max(0, limit - used)}

    @app.get("/api/v1/usage")
    async def usage(request: Request):
        return usage_view(await require_user(request))

    # ================================================================== ACCOUNT (GDPR Art. 15/17/20)
    @app.get("/api/v1/account/export")
    async def account_export(request: Request):
        sess = await require_user(request)
        uid = sess["user_id"]
        user = db.one("SELECT email, plan, created_at, last_login_at FROM users WHERE id=?", (uid,))
        mappings = []
        for r in db.all("SELECT id, provider, model, mapping_json, columns_json, save_for_reuse, confirmed, created_at, updated_at "
                        "FROM mappings WHERE user_id=? ORDER BY created_at", (uid,)):
            mappings.append({"mapping_id": r["id"], "provider": r["provider"], "model": r["model"],
                             "mapping": json.loads(r["mapping_json"]), "columns": json.loads(r["columns_json"]),
                             "save_for_reuse": bool(r["save_for_reuse"]), "confirmed": bool(r["confirmed"]),
                             "created_at": clock.iso(r["created_at"]), "updated_at": clock.iso(r["updated_at"])})
        usage_rows = [{"month": r["month"], "valid_invoices": r["valid_count"]}
                      for r in db.all("SELECT month, valid_count FROM usage WHERE user_id=? ORDER BY month", (uid,))]
        body = {"export_created_at": clock.iso(clock.now()), "product": b["product"],
                "account": {"email": user["email"], "plan": user["plan"], "created_at": clock.iso(user["created_at"]),
                            "last_login_at": clock.iso(user["last_login_at"])},
                "seller_profile": get_profile(uid), "mappings": mappings, "usage": usage_rows,
                "note_de": "Zuordnungen enthalten nur Spaltennamen, feste Werte und Umwandlungen, keine Zellinhalte. "
                           "Hochgeladene Dateien und erzeugte Rechnungen werden nach 24 Stunden gelöscht und sind nicht enthalten."}
        return JSONResponse(body, headers={"Content-Disposition": 'attachment; filename="belegbruecke-datenexport.json"'})

    @app.delete("/api/v1/account")
    async def account_delete(request: Request):
        sess = await require_user(request)
        await run_in_threadpool(runner.delete_account, sess["user_id"])
        resp = JSONResponse({"status": "deleted", "message_de": "Ihr Konto und alle zugehörigen Daten wurden gelöscht."})
        resp.delete_cookie(SESSION_COOKIE, path="/")
        return resp

    # ================================================================== PAGES
    @app.get("/", include_in_schema=False)
    async def root(request: Request):
        return RedirectResponse("/app" if current(request) else "/login", status_code=303)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if current(request):
            return RedirectResponse("/app", status_code=303)
        pre, new = ensure_pre(request)
        resp = page(request, "login.html", {"sent": request.query_params.get("gesendet") == "1",
                                            "deleted": request.query_params.get("geloescht") == "1"}, pre=pre)
        if new:
            set_cookie(resp, PRE_COOKIE, pre, 3600)
        return resp

    @app.get("/bestaetigt", response_class=HTMLResponse)
    async def bestaetigt(request: Request):
        return page(request, "message.html", {"title": "Danke, Ihre Anmeldung ist bestätigt",
                                              "text": "Sie erhalten in Kürze eine erste E-Mail. Abmelden können Sie sich jederzeit "
                                                      "über den Link in jeder E-Mail."})

    @app.get("/app", response_class=HTMLResponse)
    async def dashboard(request: Request):
        sess = current(request)
        if not sess:
            return login_redirect()
        jobs = []
        for j in db.all("SELECT * FROM jobs WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (sess["user_id"],)):
            jobs.append({"id": j["id"], "status": j["status"], "created": clock.de_datetime(j["created_at"]),
                         "invoices": j["invoice_count"], "valid": j["valid_count"]})
        return page(request, "dashboard.html", {"usage": usage_view(sess), "jobs": jobs,
                                                "has_profile": get_profile(sess["user_id"]) is not None}, sess=sess)

    @app.get("/app/profile", response_class=HTMLResponse)
    async def profile_page(request: Request):
        sess = current(request)
        if not sess:
            return login_redirect()
        return page(request, "profile.html", {"profile": get_profile(sess["user_id"]) or {}}, sess=sess)

    @app.get("/app/upload", response_class=HTMLResponse)
    async def upload_page(request: Request):
        sess = current(request)
        if not sess:
            return login_redirect()
        return page(request, "upload.html", {"has_profile": get_profile(sess["user_id"]) is not None}, sess=sess)

    @app.get("/app/mapping/{mapping_id}", response_class=HTMLResponse)
    async def mapping_page(mapping_id: str, request: Request):
        from mapping.targets import GERMAN_LABELS, HEADER_TARGETS, LINE_TARGETS, REQUIRED_TARGETS, TRANSFORMS
        sess = current(request)
        if not sess:
            return login_redirect()
        row = db.one("SELECT * FROM mappings WHERE id=? AND user_id=?", (mapping_id, sess["user_id"]))
        if not row:
            raise StarletteHTTPException(404)
        m = json.loads(row["mapping_json"])
        columns = json.loads(row["columns_json"])
        upload = db.one("SELECT * FROM uploads WHERE id=? AND user_id=?", (row["upload_id"], sess["user_id"]))
        upload_available = bool(upload and upload["path"] and Path(upload["path"]).exists())
        samples = {}
        if upload_available:
            if upload["samples_json"]:
                samples = json.loads(upload["samples_json"])  # parsed once at upload
            else:  # uploads from before the cache column
                try:
                    samples = column_samples(await read_upload_table(dict(upload)))
                except ApiError:
                    pass
        by_target = {f["target"]: f for f in m["fields"]}
        all_targets = HEADER_TARGETS + LINE_TARGETS
        required = [t for t in CONVERT_REQUIRED if t in all_targets]
        required += [t for t in (m.get("unmapped_required") or []) if isinstance(t, str) and t in all_targets
                     and t not in required and t not in XR_REQUIRED]
        rows = []
        for t in all_targets:
            f = by_target.get(t, {})
            conf = f.get("confidence")
            level = None if conf is None else ("hoch" if conf >= 0.8 else "mittel" if conf >= 0.5 else "niedrig")
            rows.append({"target": t, "label": GERMAN_LABELS.get(t, t),
                         "required": t in REQUIRED_TARGETS or t in required or t in XR_REQUIRED,
                         "line": t.startswith("/lines/"), "source_column": f.get("source_column"), "constant": f.get("constant"),
                         "transform": f.get("transform", []), "transform_de": [TRANSFORM_DE.get(x, x) for x in f.get("transform", [])],
                         "confidence": conf, "level": level, "reason_de": f.get("reason_de", ""),
                         "choices": CONST_CHOICES.get(t)})
        warnings, seen = [], set()
        for w in m.get("warnings") or []:
            if isinstance(w, dict) and isinstance(w.get("reason_de"), str) and w["reason_de"] not in seen:
                seen.add(w["reason_de"])
                warnings.append({"target": w.get("target"), "reason_de": w["reason_de"][:300]})
        no_delivery = "/delivery_date" not in by_target and "/period/start" not in by_target
        if no_delivery and not any(w.get("target") in ("/delivery_date", "/period/start", "/period") for w in warnings):
            warnings.append({"target": "/delivery_date", "reason_de": NO_DELIVERY_DATE_DE})
        prof = get_profile(sess["user_id"]) or {}
        order = ["doc_type", "strip", "upper", "de_decimal", "en_decimal", "date_dmy", "date_iso", "abs", "gross_to_net",
                 "rate_to_category", "unit_map"]
        return page(request, "mapping.html", {
            "mapping": m, "mapping_id": mapping_id, "columns": columns, "rows": rows, "samples": samples,
            "upload": dict(upload) if upload else None, "upload_available": upload_available,
            "ai": m.get("provider") == "anthropic", "ai_configured": settings.ai_provider == "anthropic",
            "transforms": [(x, TRANSFORM_DE.get(x, x)) for x in order if x in TRANSFORMS],
            "zugferd_available": settings.zugferd_available, "has_profile": bool(prof),
            "default_profile": prof.get("defaults", {}).get("profile", "xrechnung"),
            "save_for_reuse": bool(row["save_for_reuse"]),
            "warnings": warnings, "no_delivery": no_delivery,
            "js_data": {"mapping_id": mapping_id, "upload_id": upload["id"] if upload else None, "columns": columns,
                        "samples": samples, "grouping": m.get("grouping"), "required": required,
                        "required_xrechnung": XR_REQUIRED, "order": [x for x in order if x in TRANSFORMS]},
        }, sess=sess)

    @app.get("/app/jobs/{job_id}", response_class=HTMLResponse)
    async def job_page(job_id: str, request: Request):
        sess = current(request)
        if not sess:
            return login_redirect()
        job = db.one("SELECT * FROM jobs WHERE id=? AND user_id=?", (job_id, sess["user_id"]))
        if not job:
            raise StarletteHTTPException(404)
        return page(request, "job.html", {"job": job_view(job), "usage": usage_view(sess)}, sess=sess)

    @app.get("/hilfe", response_class=HTMLResponse)
    async def help_index(request: Request):
        return page(request, "help_index.html", {})

    @app.get("/hilfe/{slug}", response_class=HTMLResponse)
    async def help_page(slug: str, request: Request):
        art = articles().get(slug)
        if not art:
            raise StarletteHTTPException(404)
        return page(request, "help_page.html", {"article": art})

    return app


_app: FastAPI | None = None


def __getattr__(name: str):
    """`app.main:app` is created on first access, so importing create_app has no side effects."""
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(name)
