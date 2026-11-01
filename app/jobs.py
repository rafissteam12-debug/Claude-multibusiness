"""Conversion jobs (in-process thread pool), usage counting and retention purge.

Conversion: read_table -> apply(saved mapping) -> per invoice build_cii(profile) (+ build_zugferd)
-> validate -> Report (+ totals_warning) -> outputs in TEMP_DIR. Only `valid` files are offered as
e-invoices, and only up to the plan limit. Nothing about invoice contents is logged.
"""
from __future__ import annotations

import io
import json
import logging
import re
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import clock
from .db import Database
from .security import Security
from .settings import MAX_INVOICES_PER_JOB, PLAN_LIMITS, Settings

log = logging.getLogger("app.jobs")

FORMAT_FILES = {
    "xrechnung-cii": ("xml", "application/xml"),
    "zugferd": ("pdf", "application/pdf"),
    "pdf": ("pdf", "application/pdf"),
    "zip": ("zip", "application/zip"),
}
UNAVAILABLE_ZUGFERD = "ZUGFeRD ist in dieser Installation noch nicht verfügbar. Die XRechnung wird trotzdem erzeugt."
LIMIT_MSG = ("Gültig, aber Ihr Monatslimit ist erreicht. Diese Rechnung wird nicht als E-Rechnung angeboten "
             "und nicht gezählt.")


def safe_name(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", text or "rechnung").strip("._") or "rechnung"
    return s[:80]


class JobRunner:
    def __init__(self, settings: Settings, db: Database, security: Security, workers: int = 2):
        self.s = settings
        self.db = db
        self.sec = security
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="bb-job")
        self.usage_lock = threading.Lock()
        self._stop = threading.Event()
        self._timer: threading.Thread | None = None

    # ------------------------------------------------------------------ paths
    @property
    def upload_dir(self) -> Path:
        return self.s.temp_dir / "uploads"

    @property
    def output_dir(self) -> Path:
        return self.s.temp_dir / "outputs"

    # ------------------------------------------------------------------ usage
    def plan_limit(self, plan: str) -> int:
        return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    def used(self, user_id: str, month: str | None = None) -> int:
        row = self.db.one("SELECT valid_count FROM usage WHERE user_id=? AND month=?", (user_id, month or clock.month_key()))
        return row["valid_count"] if row else 0

    def reserve(self, user_id: str, plan: str) -> bool:
        """Count one valid invoice against this month's limit; False if the limit is reached."""
        month = clock.month_key()
        with self.usage_lock, self.db.tx() as conn:
            row = conn.execute("SELECT valid_count FROM usage WHERE user_id=? AND month=?", (user_id, month)).fetchone()
            n = row["valid_count"] if row else 0
            if n >= self.plan_limit(plan):
                return False
            conn.execute("INSERT INTO usage (user_id, month, valid_count) VALUES (?,?,1) "
                         "ON CONFLICT(user_id, month) DO UPDATE SET valid_count=valid_count+1", (user_id, month))
            return True

    # ------------------------------------------------------------------ jobs
    def submit(self, job_id: str):
        return self.pool.submit(self._run_safe, job_id)

    def _run_safe(self, job_id: str) -> None:
        try:
            self.run(job_id)
        except Exception as exc:  # never log contents, only the class
            log.error("job failed: %s", type(exc).__name__)
            self.db.execute("UPDATE jobs SET status='failed', error_de=?, finished_at=? WHERE id=? AND status!='expired'",
                            ("Die Umwandlung ist mit einem internen Fehler abgebrochen. Bitte versuchen Sie es erneut.",
                             clock.now(), job_id))

    def _store(self, job_id: str, user_id: str, kind: str, filename: str, data: bytes) -> str:
        fid = Security.new_id()
        ext, media = FORMAT_FILES[kind]
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{fid}.{ext}"
        path.write_bytes(data)
        self.db.execute("INSERT INTO files (id, job_id, user_id, kind, filename, media_type, path, created_at) VALUES (?,?,?,?,?,?,?,?)",
                        (fid, job_id, user_id, kind, filename, media, str(path), clock.now()))
        return fid

    def run(self, job_id: str) -> None:
        import engine
        import mapping

        job = self.db.one("SELECT j.*, u.plan FROM jobs j JOIN users u ON u.id=j.user_id WHERE j.id=?", (job_id,))
        if not job or job["status"] != "queued":
            return
        self.db.execute("UPDATE jobs SET status='running', started_at=? WHERE id=?", (clock.now(), job_id))
        user_id, plan = job["user_id"], job["plan"]
        formats = json.loads(job["formats"])
        profile_name = job["profile"]

        def fail(msg: str):
            self.db.execute("UPDATE jobs SET status='failed', error_de=?, finished_at=? WHERE id=?", (msg, clock.now(), job_id))

        upload = self.db.one("SELECT * FROM uploads WHERE id=?", (job["upload_id"],))
        if not upload or not upload["path"] or not Path(upload["path"]).exists():
            return fail("Die hochgeladene Datei ist nicht mehr vorhanden. Bitte laden Sie sie erneut hoch.")
        mrow = self.db.one("SELECT mapping_json FROM mappings WHERE id=?", (job["mapping_id"],))
        prow = self.db.one("SELECT profile_json FROM seller_profiles WHERE user_id=?", (user_id,))
        if not mrow or not prow:
            return fail("Zuordnung oder Unternehmensprofil fehlt.")
        mp = json.loads(mrow["mapping_json"])
        seller_profile = json.loads(prow["profile_json"])
        try:
            table = mapping.read_table(Path(upload["path"]).read_bytes(), upload["filename"] or f"upload.{upload['ext']}")
            invoices, row_errors = mapping.apply(table, mp, seller_profile)
        except (mapping.TableReadError, mapping.MappingError) as exc:
            return fail(getattr(exc, "message_de", None) or "Die Datei konnte mit dieser Zuordnung nicht gelesen werden.")
        if len(invoices) > MAX_INVOICES_PER_JOB:
            return fail(f"Die Datei enthält mehr als {MAX_INVOICES_PER_JOB} Rechnungen. Bitte teilen Sie sie auf.")

        results, offered_ids, valid_count = [], [], 0
        for inv in invoices:
            res = self._convert_one(engine, job_id, user_id, plan, inv, formats, profile_name)
            if res["valid"]:
                valid_count += 1
            offered_ids += [fid for k, fid in res.pop("_offered", [])]
            results.append(res)

        zip_id = None
        if offered_ids:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for fid in offered_ids:
                    f = self.db.one("SELECT filename, path FROM files WHERE id=?", (fid,))
                    zf.write(f["path"], f["filename"])
            zip_id = self._store(job_id, user_id, "zip", "e-rechnungen.zip", buf.getvalue())

        out = {
            "invoices": results,
            "row_errors": [{"row": e.row, "column": e.column, "field": e.field, "code": e.code, "message_de": e.message_de}
                           for e in row_errors],
            "zip_file_id": zip_id,
            "formats_unavailable": sorted({k for r in results for k, v in r["formats"].items() if v["status"] == "unavailable"}),
        }
        now = clock.now()
        self.db.execute("UPDATE jobs SET status='done', result_json=?, invoice_count=?, valid_count=?, finished_at=? WHERE id=?",
                        (json.dumps(out, ensure_ascii=False), len(invoices), valid_count, now, job_id))
        # Retention: raw upload deleted at successful conversion.
        self.delete_upload(upload["id"])
        self.db.execute("INSERT INTO events (name, path, code, created_at) VALUES ('conversion_done', '/app/jobs', NULL, ?)", (now,))

    def _convert_one(self, engine, job_id, user_id, plan, inv, formats, profile_name) -> dict:
        number = inv.get("number", "")
        base = safe_name(number)
        res = {"number": number, "valid": False, "errors": [], "warnings": [], "layers": [], "totals_warning": None,
               "formats": {}, "download_urls": {}, "counted": False, "limit_reached": False, "_offered": []}
        try:
            xml = engine.build_cii(inv, profile=profile_name)
        except engine.InvoiceInputError as exc:
            res["errors"] = [{"id": e.code, "message_de": e.message_de, "location": e.field, "layer": "Eingabe"} for e in exc.errors]
            res["input_error"] = True
            for f in formats:
                res["formats"][f] = {"status": "invalid", "message_de": "Nicht erzeugt: Angaben fehlen oder sind ungültig."}
            self._readable_pdf(engine, res, job_id, user_id, inv, base)
            return res
        report = engine.validate(xml, f"{base}.xml")
        report["totals_warning"] = engine.totals_warning(inv)
        res["valid"] = bool(report["valid"])
        res["layers"] = report["layers"]
        res["totals_warning"] = report["totals_warning"]
        res["profile"] = report["profile"]
        for layer in report["layers"]:
            res["errors"] += [dict(e, layer=layer["name"]) for e in layer["errors"]]
            res["warnings"] += [dict(e, layer=layer["name"]) for e in layer["warnings"]]

        candidates = []  # (kind, filename, bytes) valid e-invoice files
        if "xrechnung-cii" in formats:
            if res["valid"]:
                candidates.append(("xrechnung-cii", f"{base}.xml", xml))
            else:
                res["formats"]["xrechnung-cii"] = {"status": "invalid", "message_de": "Nicht gültig – siehe Fehler."}
        if "zugferd" in formats:
            if not res["valid"]:
                res["formats"]["zugferd"] = {"status": "invalid", "message_de": "Nicht erzeugt, weil die Daten nicht gültig sind."}
            else:
                try:
                    pdf = engine.build_zugferd(inv)
                    zrep = engine.validate(pdf, f"{base}.pdf")
                    if zrep["valid"]:
                        candidates.append(("zugferd", f"{base}-zugferd.pdf", pdf))
                    else:
                        res["formats"]["zugferd"] = {"status": "invalid", "message_de": "Die ZUGFeRD-Datei hat die Prüfung nicht bestanden."}
                except engine.FeatureUnavailable:
                    res["formats"]["zugferd"] = {"status": "unavailable", "message_de": UNAVAILABLE_ZUGFERD}
                except engine.InvoiceInputError:
                    res["formats"]["zugferd"] = {"status": "invalid", "message_de": "ZUGFeRD konnte aus diesen Daten nicht erzeugt werden."}
        if candidates:
            if self.reserve(user_id, plan):
                res["counted"] = True
                for kind, fname, data in candidates:
                    fid = self._store(job_id, user_id, kind, fname, data)
                    res["formats"][kind] = {"status": "valid", "message_de": "Gültig."}
                    res["download_urls"][kind] = f"/api/v1/files/{fid}"
                    res["_offered"].append((kind, fid))
            else:
                res["limit_reached"] = True
                for kind, _, _ in candidates:
                    res["formats"][kind] = {"status": "limit", "message_de": LIMIT_MSG}
        self._readable_pdf(engine, res, job_id, user_id, inv, base)
        return res

    def _readable_pdf(self, engine, res, job_id, user_id, inv, base) -> None:
        """Readable PDF for checking the content; always labelled 'keine E-Rechnung'."""
        try:
            pdf = engine.render_pdf(inv)
        except Exception as exc:
            log.info("readable pdf not rendered: %s", type(exc).__name__)
            return
        fid = self._store(job_id, user_id, "pdf", f"{base}-lesbar-keine-e-rechnung.pdf", pdf)
        res["download_urls"]["pdf"] = f"/api/v1/files/{fid}"

    # ------------------------------------------------------------------ retention
    def delete_upload(self, upload_id: str) -> None:
        row = self.db.one("SELECT path FROM uploads WHERE id=?", (upload_id,))
        if row and row["path"]:
            Path(row["path"]).unlink(missing_ok=True)
        self.db.execute("UPDATE uploads SET path=NULL, filename=NULL, deleted_at=COALESCE(deleted_at, ?) WHERE id=?",
                        (clock.now(), upload_id))

    def purge(self) -> dict:
        """Apply the retention rules (contracts/api.md). Safe to call at any time."""
        now = clock.now()
        cutoff = now - self.s.retention_seconds
        counts = {"uploads": 0, "files": 0, "jobs": 0}
        for row in self.db.all("SELECT id FROM uploads WHERE deleted_at IS NULL AND created_at<?", (cutoff,)):
            self.delete_upload(row["id"])
            counts["uploads"] += 1
        for row in self.db.all("SELECT id, path FROM files WHERE deleted_at IS NULL AND created_at<?", (cutoff,)):
            if row["path"]:
                Path(row["path"]).unlink(missing_ok=True)
            self.db.execute("UPDATE files SET path=NULL, filename=NULL, deleted_at=? WHERE id=?", (now, row["id"]))
            counts["files"] += 1
        counts["jobs"] = self.db.execute(
            "UPDATE jobs SET status='expired', result_json=NULL, error_de=NULL, expired_at=? "
            "WHERE status!='expired' AND created_at<? AND status NOT IN ('queued','running')", (now, cutoff))
        self.db.execute("DELETE FROM tokens WHERE expires_at<?", (now - 3600,))
        self.db.execute("DELETE FROM sessions WHERE expires_at<?", (now,))
        self.db.execute("DELETE FROM rate_hits WHERE created_at<?", (now - 2 * 86400,))
        # Unconfirmed opt-in requests are kept 7 days as a record of the request, then removed.
        self.db.execute("DELETE FROM subscribers WHERE confirmed_at IS NULL AND requested_at<?", (now - 7 * 86400,))
        # Leftover files in TEMP_DIR (e.g. after a crash) older than the retention period.
        for d in (self.upload_dir, self.output_dir):
            if d.exists():
                for f in d.iterdir():
                    try:
                        # mtime is wall-clock; shift it by the test clock offset
                        if f.is_file() and f.stat().st_mtime + (now - time.time()) < cutoff:
                            f.unlink()
                    except OSError:
                        pass
        return counts

    def start_timer(self, interval: float = 600, tick=None) -> None:
        def loop():
            while not self._stop.wait(interval):
                try:
                    self.purge()
                    if tick:
                        tick()
                except Exception as exc:
                    log.error("purge failed: %s", type(exc).__name__)
        self._timer = threading.Thread(target=loop, name="bb-purge", daemon=True)
        self._timer.start()

    def shutdown(self) -> None:
        self._stop.set()
        self.pool.shutdown(wait=True, cancel_futures=False)
