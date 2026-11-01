"""SQLite storage (stdlib sqlite3) with a tiny migration system.

Migrations are numbered SQL files in app/migrations (001_init.sql, 002_...). Applied versions
are recorded in `schema_migrations`. One short-lived connection per operation (thread-safe).
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.write_lock = threading.RLock()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA secure_delete = ON")  # purged rows (error texts, samples) are overwritten, not left in free pages
        return conn

    @contextmanager
    def tx(self):
        """A write transaction (BEGIN IMMEDIATE), serialised within the process."""
        with self.write_lock:
            conn = self.connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            finally:
                conn.close()

    def one(self, sql: str, params=()) -> sqlite3.Row | None:
        conn = self.connect()
        try:
            return conn.execute(sql, params).fetchone()
        finally:
            conn.close()

    def all(self, sql: str, params=()) -> list[sqlite3.Row]:
        conn = self.connect()
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def execute(self, sql: str, params=()) -> int:
        with self.tx() as conn:
            return conn.execute(sql, params).rowcount

    def migrate(self) -> list[str]:
        """Apply pending migrations in order; returns the applied file names."""
        applied_now = []
        with self.write_lock:
            conn = self.connect()
            try:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
                done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
                for f in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
                    if f.name in done:
                        continue
                    conn.execute("BEGIN IMMEDIATE")
                    try:
                        for stmt in _split_sql(f.read_text(encoding="utf-8")):
                            conn.execute(stmt)
                        conn.execute("INSERT INTO schema_migrations VALUES (?, datetime('now'))", (f.name,))
                        conn.execute("COMMIT")
                    except BaseException:
                        conn.execute("ROLLBACK")
                        raise
                    applied_now.append(f.name)
            finally:
                conn.close()
        return applied_now


def _split_sql(text: str) -> list[str]:
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    out, buf = [], []
    for ln in lines:
        code = ln.split("--", 1)[0]
        buf.append(code)
        if code.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";")
            if stmt:
                out.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        out.append(tail)
    return out
