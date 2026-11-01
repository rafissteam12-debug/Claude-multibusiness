#!/usr/bin/env python3
"""Strict 14-day retention for the Caddy access log (owner decision; ops/RUNBOOK.md "Log retention: 14 days").

Runs in the `logretention` service of ops/docker-compose.yml: once at start, then daily at 00:05 UTC.
Stdlib only. Prints counts only, never log lines (they hold masked IPs and URLs).

What one run does in the log directory (default /var/log/caddy):

1. Daily rotation of the active file `access.log` (copy-truncate). If it holds a line from before today
   (UTC), its whole content is read and the file is truncated to 0 bytes right after the read. The lines are
   then filed by their own timestamp (`ts`) into `access-day-YYYY-MM-DD.log` (appended, so a later run adds
   to the same day file). After a rotation the active file is empty, so it never holds lines older than the
   last run. A second run on the same day finds only today's lines and does nothing (idempotent).

   Why copy-truncate and not rename + `caddy reload`: Caddy 2.10 keeps log writers open across config
   reloads (they are pooled per file name), so a renamed file would keep receiving lines; a reload would also
   need the admin API reachable from another container. Caddy opens the file with O_APPEND
   (modules/logging/filewriter.go), so after the truncate its next write lands at offset 0: no hole, no
   overwritten bytes. Every byte read is removed by the truncate, so no line is ever filed twice. The one
   residual race: a line Caddy appends in the microseconds between the final read and the truncate would be
   lost. To keep that window away from traffic the run first waits for a quiet moment (file size unchanged
   for `--quiet-seconds`), and the read and truncate are two back-to-back syscalls on the same descriptor.

2. Retention over every log file in the directory (the day files, Caddy's own size-rolled
   `access-<timestamp>.log[.gz]`, and the active file): a line whose `ts` is older than `--days` (14) is
   removed; a file whose newest line is older is deleted; a file without any readable timestamp is judged by
   its mtime. Files are rewritten atomically (temp file + rename), gzip stays gzip. With one run per day no
   line survives longer than 14 days + 1 day.

Never touched: files whose names do not match the log patterns below, directories, symlinks.

Usage:
  python log_retention.py --dir /var/log/caddy --once          one run, then exit
  python log_retention.py --dir /var/log/caddy                 run now, then daily at --at (UTC)
  python log_retention.py --dir DIR --now 2026-11-01T00:05:00Z --once   fixed clock (CI fixture)
  python log_retention.py --dir DIR --verify                   exit 1 if any line/file is over the limit
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

ACTIVE = "access.log"
DAY_RE = re.compile(r"^access-day-(\d{4}-\d{2}-\d{2})\.log$")
# Caddy (lumberjack/timberjack) rolled files: access-2006-01-02T15-04-05.000[-reason].log[.gz]
CADDY_ROLLED_RE = re.compile(r"^access-\d{4}-\d{2}-\d{2}T[\w.-]+\.log(\.gz)?$")
TMP_PREFIX = ".log_retention-"
# A size-rolled file younger than this may still be compressed by Caddy; it is handled on the next run.
FRESH_ROLLED_SECONDS = 300


@dataclass
class Stats:
    rotated_lines: int = 0
    day_files_written: int = 0
    lines_dropped: int = 0
    files_deleted: int = 0
    files_rewritten: int = 0
    skipped_fresh: int = 0
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (f"rotated_lines={self.rotated_lines} day_files_written={self.day_files_written} "
                f"lines_dropped={self.lines_dropped} files_deleted={self.files_deleted} "
                f"files_rewritten={self.files_rewritten} skipped_fresh={self.skipped_fresh}")


def line_ts(line: bytes) -> float | None:
    """Unix timestamp of one JSON log line (Caddy's `ts`, float seconds), or None if unreadable."""
    try:
        obj = json.loads(line)
    except (ValueError, UnicodeDecodeError):
        return None
    ts = obj.get("ts") if isinstance(obj, dict) else None
    if isinstance(ts, (int, float)) and not isinstance(ts, bool):
        return float(ts)
    if isinstance(ts, str):  # ISO format, if the encoder is ever switched to time_format iso8601
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
        return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp()
    return None


def split_lines(data: bytes) -> list[bytes]:
    """Lines including their newline; a trailing partial line gets one (Caddy writes a line per syscall)."""
    lines = data.splitlines(keepends=True)
    if lines and not lines[-1].endswith(b"\n"):
        lines[-1] += b"\n"
    return [ln for ln in lines if ln.strip()]


def stamp(lines: list[bytes], fallback: float) -> list[tuple[float, bytes]]:
    """Timestamp per line; an unreadable line inherits the previous line's ts (or the first readable / fallback)."""
    raw = [line_ts(ln) for ln in lines]
    first = next((t for t in raw if t is not None), fallback)
    out, prev = [], first
    for t, ln in zip(raw, lines):
        prev = t if t is not None else prev
        out.append((prev, ln))
    return out


def utc_day(ts: float) -> date:
    return datetime.fromtimestamp(ts, timezone.utc).date()


def is_log_file(name: str) -> bool:
    return name == ACTIVE or bool(DAY_RE.match(name) or CADDY_ROLLED_RE.match(name))


def _read(path: Path) -> bytes:
    if path.name.endswith(".gz"):
        with gzip.open(path, "rb") as f:
            return f.read()
    return path.read_bytes()


def _atomic_write(path: Path, data: bytes) -> None:
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o640
    fd, tmp = tempfile.mkstemp(prefix=TMP_PREFIX, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            if path.name.endswith(".gz"):
                with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as gz:
                    gz.write(data)
            else:
                f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _wait_quiet(path: Path, quiet: float, max_wait: float, sleep: Callable[[float], None]) -> None:
    """Wait until the file size has not changed for `quiet` seconds (at most `max_wait`)."""
    if quiet <= 0:
        return
    waited, last = 0.0, path.stat().st_size
    still = 0.0
    step = min(0.5, quiet)
    while still < quiet and waited < max_wait:
        sleep(step)
        waited += step
        size = path.stat().st_size
        still = still + step if size == last else 0.0
        last = size


def rotate_active(log_dir: Path, now: float, cutoff: float, stats: Stats, quiet: float = 2.0,
                  max_wait: float = 60.0, sleep: Callable[[float], None] = time.sleep) -> None:
    active = log_dir / ACTIVE
    if not active.is_file() or active.is_symlink() or active.stat().st_size == 0:
        return
    today = utc_day(now)
    # Decide without modifying: rotate only if some line is from before today (idempotent within a day).
    peek = stamp(split_lines(active.read_bytes()), active.stat().st_mtime)
    if not any(utc_day(ts) < today for ts, _ in peek):
        return
    _wait_quiet(active, quiet, max_wait, sleep)
    with open(active, "r+b") as f:
        data = f.read()
        f.truncate(0)          # immediately after the read, same descriptor (see module docstring)
    lines = stamp(split_lines(data), now)
    by_day: dict[date, list[bytes]] = {}
    for ts, ln in lines:
        if ts < cutoff:
            stats.lines_dropped += 1
            continue
        by_day.setdefault(utc_day(ts), []).append(ln)
    for day, chunk in sorted(by_day.items()):
        target = log_dir / f"access-day-{day.isoformat()}.log"
        new = not target.exists()
        with open(target, "ab") as out:
            out.write(b"".join(chunk))
            out.flush()
            os.fsync(out.fileno())
        if new:
            os.chmod(target, 0o640)
        stats.rotated_lines += len(chunk)
        stats.day_files_written += 1


def prune_file(path: Path, now: float, cutoff: float, stats: Stats) -> None:
    """Drop lines older than cutoff; delete the file if nothing young is left."""
    st = path.lstat()
    m = DAY_RE.match(path.name)
    if m:  # fast path: every line of a day file is from that UTC day
        day_end = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc) + timedelta(days=1)
        if day_end.timestamp() <= cutoff:
            path.unlink()
            stats.files_deleted += 1
            return
    elif CADDY_ROLLED_RE.match(path.name) and 0 <= now - st.st_mtime < FRESH_ROLLED_SECONDS:
        stats.skipped_fresh += 1
        return
    try:
        lines = split_lines(_read(path))
    except (OSError, EOFError, gzip.BadGzipFile):
        # Unreadable (e.g. a broken gzip): judge by mtime only, never keep it past the limit.
        if st.st_mtime < cutoff:
            path.unlink()
            stats.files_deleted += 1
        return
    if not lines or all(line_ts(ln) is None for ln in lines):
        if st.st_mtime < cutoff and path.name != ACTIVE:
            path.unlink()
            stats.files_deleted += 1
        return
    stamped = stamp(lines, st.st_mtime)
    keep = [ln for ts, ln in stamped if ts >= cutoff]
    dropped = len(stamped) - len(keep)
    if not dropped:
        return
    stats.lines_dropped += dropped
    if not keep:
        path.unlink()
        stats.files_deleted += 1
    else:
        _atomic_write(path, b"".join(keep))
        stats.files_rewritten += 1


def clean_own_temp_files(log_dir: Path, now: float) -> None:
    for p in log_dir.iterdir():
        if p.name.startswith(TMP_PREFIX) and p.is_file() and not p.is_symlink() and now - p.lstat().st_mtime > 3600:
            p.unlink()


def run(log_dir: Path, now: float | None = None, days: int = 14, quiet: float = 2.0,
        sleep: Callable[[float], None] = time.sleep) -> Stats:
    now = time.time() if now is None else now
    cutoff = now - days * 86400
    stats = Stats()
    if not log_dir.is_dir():
        stats.notes.append("log directory missing")
        return stats
    clean_own_temp_files(log_dir, now)
    rotate_active(log_dir, now, cutoff, stats, quiet=quiet, sleep=sleep)
    for p in sorted(log_dir.iterdir()):
        if p.name == ACTIVE or not is_log_file(p.name) or p.is_symlink() or not p.is_file():
            continue
        prune_file(p, now, cutoff, stats)
    return stats


def violations(log_dir: Path, now: float | None = None, days: int = 14, slack_days: int = 0) -> list[str]:
    """Problems that a correct daily run must not leave behind (for --verify and tests). No line contents."""
    now = time.time() if now is None else now
    cutoff = now - (days + slack_days) * 86400
    today = utc_day(now)
    found = []
    for p in sorted(log_dir.iterdir()):
        if not is_log_file(p.name) or p.is_symlink() or not p.is_file():
            continue
        try:
            lines = split_lines(_read(p))
        except (OSError, EOFError, gzip.BadGzipFile):
            if p.lstat().st_mtime < cutoff:
                found.append(f"{p.name}: unreadable and older than limit")
            continue
        stamped = stamp(lines, p.lstat().st_mtime)
        old = sum(1 for ts, _ in stamped if ts < cutoff)
        if old:
            found.append(f"{p.name}: {old} line(s) older than {days + slack_days} days")
        if p.name == ACTIVE and any(utc_day(ts) < today for ts, _ in stamped):
            found.append(f"{p.name}: holds lines from before today (rotation missing)")
    return found


def parse_now(value: str) -> float:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp()


def seconds_until(at: str, now: float) -> float:
    hh, mm = (int(x) for x in at.split(":"))
    cur = datetime.fromtimestamp(now, timezone.utc)
    nxt = cur.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if nxt <= cur:
        nxt += timedelta(days=1)
    return (nxt - cur).total_seconds()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", type=Path, default=Path("/var/log/caddy"))
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--at", default="00:05", help="daily run time, HH:MM UTC (loop mode)")
    ap.add_argument("--now", help="fixed clock, ISO 8601 (tests/CI only)")
    ap.add_argument("--quiet-seconds", type=float, default=2.0)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--verify", action="store_true", help="only check, exit 1 on any violation")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", a.at) or a.days < 1:
        ap.error("--at must be HH:MM and --days >= 1")
    fixed = parse_now(a.now) if a.now else None

    if a.verify:
        found = violations(a.dir, fixed, a.days)
        for v in found:
            print(f"log_retention: VIOLATION {v}", file=sys.stderr)
        print(f"log_retention: verify {'failed' if found else 'ok'} ({len(found)} problem(s))")
        return 1 if found else 0

    while True:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            stats = run(a.dir, fixed, a.days, a.quiet_seconds)
            print(f"{ts} log_retention: ok {stats.summary()}" + (f" note={';'.join(stats.notes)}" if stats.notes else ""),
                  flush=True)
        except Exception as exc:  # keep the loop alive; class name only, never content
            print(f"{ts} log_retention: ERROR {type(exc).__name__} - retention at risk", file=sys.stderr, flush=True)
            if a.once:
                return 1
        if a.once:
            return 0
        time.sleep(min(seconds_until(a.at, time.time()), 6 * 3600) + 1)


if __name__ == "__main__":
    sys.exit(main())
