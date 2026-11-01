"""Behavioural tests for ops/scripts/log_retention.py (strict 14-day Caddy access-log retention).

Temp directory + injected clock; no Docker, no network. Log lines are fictional (masked documentation IPs,
.invalid host).
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "ops"
FIXTURE = OPS / "tests" / "fixtures" / "caddy_logs"

_spec = importlib.util.spec_from_file_location("ops_log_retention", OPS / "scripts" / "log_retention.py")
lr = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lr  # dataclasses need the module registered
_spec.loader.exec_module(lr)

NOW = datetime(2026, 11, 1, 0, 5, tzinfo=timezone.utc)
DAY = 86400.0


def ts_ago(days: float, now: datetime = NOW) -> float:
    return (now - timedelta(days=days)).timestamp()


def line(ts: float, uri: str = "/healthz") -> str:
    return json.dumps({"level": "info", "ts": ts, "logger": "http.log.access", "msg": "handled request",
                       "request": {"remote_ip": "192.0.0.0", "host": "app.example.invalid", "uri": uri},
                       "status": 200}) + "\n"


def write(path: Path, *ts: float, mtime: float | None = None) -> Path:
    path.write_text("".join(line(t, f"/r{i}") for i, t in enumerate(ts)), encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def all_ts(log_dir: Path) -> dict[str, list[float]]:
    out = {}
    for p in sorted(log_dir.iterdir()):
        if lr.is_log_file(p.name):
            out[p.name] = [lr.line_ts(ln) for ln in lr.split_lines(lr._read(p))]
    return out


def run(log_dir: Path, now: datetime = NOW):
    return lr.run(log_dir, now=now.timestamp(), days=14, quiet=0)


def snapshot(log_dir: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(log_dir.iterdir())}


# ---------------------------------------------------------------- age boundaries (13, 14, 15, 30 days)

@pytest.mark.parametrize("age,kept", [(13, True), (14, True), (14 + 1 / 1440, False), (15, False), (30, False)])
def test_line_age_boundary_in_rolled_file(tmp_path, age, kept):
    """A line exactly 14 days old is kept; one minute older is removed (no line survives > 14 days at a run)."""
    f = write(tmp_path / "access-2026-10-30T10-00-00.000.log", ts_ago(age), ts_ago(1), mtime=ts_ago(1))
    run(tmp_path)
    assert all_ts(tmp_path)[f.name] == ([ts_ago(age)] if kept else []) + [ts_ago(1)]


@pytest.mark.parametrize("age,kept", [(13, True), (14, True), (15, False), (30, False)])
def test_whole_file_deleted_when_newest_entry_too_old(tmp_path, age, kept):
    plain = write(tmp_path / "access-2026-09-01T00-00-00.000.log", ts_ago(age + 0.5), ts_ago(age), mtime=ts_ago(age))
    gz = tmp_path / "access-2026-09-02T00-00-00.000.log.gz"
    with gzip.open(gz, "wt", encoding="utf-8") as f:
        f.write(line(ts_ago(age)))
    os.utime(gz, (ts_ago(age), ts_ago(age)))
    run(tmp_path)
    assert plain.exists() is kept and gz.exists() is kept
    if kept:  # partially old file: only the young line survives, gzip stays gzip
        assert all_ts(tmp_path)[gz.name] == [ts_ago(age)]
        assert gzip.decompress(gz.read_bytes())


@pytest.mark.parametrize("age,kept", [(13, True), (14, True), (15, False), (30, False)])
def test_file_without_timestamps_judged_by_mtime(tmp_path, age, kept):
    f = tmp_path / "access-2026-09-03T00-00-00.000.log"
    f.write_text("not json\nalso not json\n", encoding="utf-8")
    os.utime(f, (ts_ago(age), ts_ago(age)))
    run(tmp_path)
    assert f.exists() is kept


def test_day_file_spanning_boundary_is_pruned_line_by_line(tmp_path):
    day = (NOW - timedelta(days=14)).date().isoformat()        # 2026-10-18: 00:05 is the cutoff
    f = tmp_path / f"access-day-{day}.log"
    cutoff = ts_ago(14)
    write(f, cutoff - 60, cutoff, cutoff + 3600)
    old = write(tmp_path / f"access-day-{(NOW - timedelta(days=15)).date().isoformat()}.log", ts_ago(14.9))
    run(tmp_path)
    assert all_ts(tmp_path)[f.name] == [cutoff, cutoff + 3600]
    assert not old.exists()


def test_long_spanning_rolled_file_keeps_only_young_lines(tmp_path):
    """One file covering 40 days (quiet period): every line older than 14 days goes, order is kept."""
    ages = [40, 30, 20, 15, 14.5, 13.9, 7, 2, 1]
    f = write(tmp_path / "access-2026-10-30T23-00-00.000.log", *(ts_ago(a) for a in ages), mtime=ts_ago(1))
    run(tmp_path)
    assert all_ts(tmp_path)[f.name] == [ts_ago(a) for a in ages if a <= 14]
    assert lr.violations(tmp_path, NOW.timestamp()) == []


# ---------------------------------------------------------------- active file: daily rotation

def test_active_file_rotated_by_day_and_emptied(tmp_path):
    ages = [30, 15, 13, 2, 1, 5 / 1440, 1 / 1440]   # last two: 00:00 and 00:04 today (UTC)
    active = write(tmp_path / "access.log", *(ts_ago(a) for a in ages))
    stats = run(tmp_path)
    assert active.exists() and active.stat().st_size == 0, "active file is truncated, not deleted"
    files = all_ts(tmp_path)
    kept = [ts_ago(a) for a in ages if a <= 14]
    assert sorted(t for v in files.values() for t in v) == sorted(kept), "no line lost, none duplicated"
    for name, values in files.items():
        m = lr.DAY_RE.match(name)
        if m:
            assert {lr.utc_day(t).isoformat() for t in values} == {m.group(1)}, "each line filed by its own day"
    assert stats.rotated_lines == len(kept) and stats.lines_dropped == 2


def test_rotation_day_boundary_utc(tmp_path):
    """23:59:59 yesterday -> yesterday's file, 00:00:00 today -> today's file; run right after midnight."""
    midnight = datetime(2026, 11, 1, tzinfo=timezone.utc)
    now = midnight + timedelta(minutes=5)
    write(tmp_path / "access.log", midnight.timestamp() - 1, midnight.timestamp(), midnight.timestamp() + 60)
    run(tmp_path, now)
    files = all_ts(tmp_path)
    assert files["access-day-2026-10-31.log"] == [midnight.timestamp() - 1]
    assert files["access-day-2026-11-01.log"] == [midnight.timestamp(), midnight.timestamp() + 60]
    assert files["access.log"] == []


def test_no_rotation_when_active_file_holds_only_todays_lines(tmp_path):
    now = datetime(2026, 11, 1, 18, 0, tzinfo=timezone.utc)
    active = write(tmp_path / "access.log", ts_ago(0.5, now), ts_ago(0.1, now))   # 06:00 and 15:36 today
    before = active.read_bytes()
    run(tmp_path, now)
    assert active.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["access.log"]


def test_next_day_appends_to_existing_day_file(tmp_path):
    """Lines of day D cut in two runs end up in one day file, in order, once each."""
    d1 = datetime(2026, 10, 31, 0, 5, tzinfo=timezone.utc)
    write(tmp_path / "access.log", ts_ago(0.6, d1))                     # Oct 30 -> rotated on Oct 31
    run(tmp_path, d1)
    # Caddy keeps appending to the (truncated) active file during Oct 31, and one more on Nov 1
    late = [datetime(2026, 10, 31, h, tzinfo=timezone.utc).timestamp() for h in (1, 12, 23)]
    with open(tmp_path / "access.log", "a", encoding="utf-8") as f:
        f.write("".join(line(t) for t in late) + line(NOW.timestamp() - 60))
    run(tmp_path, NOW)
    files = all_ts(tmp_path)
    assert files["access-day-2026-10-31.log"] == late
    assert files["access-day-2026-10-30.log"] == [ts_ago(0.6, d1)]
    assert files["access-day-2026-11-01.log"] == [NOW.timestamp() - 60]
    assert files["access.log"] == []


def test_active_file_never_keeps_old_lines_over_many_days(tmp_path):
    """Simulated month: Caddy writes every hour, retention runs daily at 00:05. Invariants hold every day."""
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    written = []
    for day in range(45):
        for hour in range(24):
            t = (start + timedelta(days=day, hours=hour, minutes=30)).timestamp()
            with open(tmp_path / "access.log", "a", encoding="utf-8") as f:
                f.write(line(t))
            written.append(t)
        now = start + timedelta(days=day + 1, minutes=5)
        run(tmp_path, now)
        assert lr.violations(tmp_path, now.timestamp()) == [], day
        files = all_ts(tmp_path)
        assert files["access.log"] == []
        present = sorted(t for v in files.values() for t in v)
        assert present == [t for t in written if t >= now.timestamp() - 14 * DAY], "exactly the last 14 days"
        assert len([n for n in files if lr.DAY_RE.match(n)]) <= 15


def test_trailing_partial_line_is_kept(tmp_path):
    (tmp_path / "access.log").write_text(line(ts_ago(1)) + line(ts_ago(0.9)).rstrip("\n"), encoding="utf-8")
    run(tmp_path)
    assert all_ts(tmp_path)["access-day-2026-10-31.log"] == [ts_ago(1), ts_ago(0.9)]


def test_unparseable_line_follows_its_neighbour(tmp_path):
    (tmp_path / "access.log").write_text(line(ts_ago(20)) + "garbage\n" + line(ts_ago(1)) + "garbage2\n",
                                         encoding="utf-8")
    run(tmp_path)
    day = (tmp_path / "access-day-2026-10-31.log").read_text(encoding="utf-8")
    assert "garbage2" in day and "garbage\n" not in day


# ---------------------------------------------------------------- idempotence and safety

def test_idempotent_second_run_changes_nothing(tmp_path):
    shutil.copytree(FIXTURE, tmp_path / "logs")
    d = tmp_path / "logs"
    for p in d.iterdir():
        os.utime(p, (ts_ago(1), ts_ago(1)))
    run(d)
    first = snapshot(d)
    stats = run(d)
    assert snapshot(d) == first
    assert stats.summary() == lr.Stats().summary()


def test_never_touches_non_log_files(tmp_path):
    old = ts_ago(60)
    others = {
        "README.txt": "notes", "other.log": line(old), "access.log.bak": line(old), "access-notes.txt": line(old),
        "access-day-2026-01-01.log.bak": line(old), "error.log": line(old), "access-day-foo.log": line(old),
    }
    for name, text in others.items():
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        os.utime(p, (old, old))
    (tmp_path / "sub").mkdir()
    write(tmp_path / "sub" / "access.log", old)
    target = write(tmp_path.parent / f"{tmp_path.name}-outside.log", old)
    (tmp_path / "access-2026-01-01T00-00-00.000.log").symlink_to(target)
    before = snapshot(tmp_path / "sub")
    run(tmp_path)
    for name, text in others.items():
        assert (tmp_path / name).read_text(encoding="utf-8") == text, name
    assert snapshot(tmp_path / "sub") == before
    assert (tmp_path / "access-2026-01-01T00-00-00.000.log").is_symlink() and target.read_text(encoding="utf-8")


def test_fresh_caddy_rolled_file_waits_for_next_run(tmp_path):
    """Caddy may still be gzipping a just-rolled file; it is left alone and handled on the next daily run."""
    f = write(tmp_path / "access-2026-11-01T00-04-00.000.log", ts_ago(20), ts_ago(0.01), mtime=NOW.timestamp() - 30)
    stats = run(tmp_path)
    assert f.exists() and stats.skipped_fresh == 1
    run(tmp_path, NOW + timedelta(days=1))
    assert all_ts(tmp_path)[f.name] == [ts_ago(0.01)]


def test_missing_directory_and_empty_active_file(tmp_path):
    assert "log directory missing" in run(tmp_path / "nope").notes
    (tmp_path / "access.log").write_bytes(b"")
    run(tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["access.log"]


def test_quiet_wait_polls_until_size_is_stable(tmp_path):
    active = write(tmp_path / "access.log", ts_ago(1))
    calls = []

    def fake_sleep(s):
        calls.append(s)
        if len(calls) == 2:  # Caddy writes once while we wait
            with open(active, "a", encoding="utf-8") as f:
                f.write(line(ts_ago(0.5)))

    lr.run(tmp_path, now=NOW.timestamp(), quiet=1.0, sleep=fake_sleep)
    assert len(calls) >= 4, "waited again after the size changed"
    assert all_ts(tmp_path)["access-day-2026-10-31.log"] == [ts_ago(1), ts_ago(0.5)]


def test_output_has_counts_only(tmp_path, capsys):
    write(tmp_path / "access.log", ts_ago(20), ts_ago(1))
    assert lr.main(["--dir", str(tmp_path), "--once", "--now", NOW.isoformat(), "--quiet-seconds", "0"]) == 0
    out = capsys.readouterr()
    assert "app.example.invalid" not in out.out + out.err and "192.0.0.0" not in out.out + out.err
    assert re.search(r"log_retention: ok rotated_lines=1 .*lines_dropped=1", out.out)


def test_verify_cli_on_fixture(tmp_path):
    d = tmp_path / "logs"
    shutil.copytree(FIXTURE, d)
    for p in d.iterdir():
        os.utime(p, (ts_ago(1), ts_ago(1)))
    args = ["--dir", str(d), "--now", "2026-11-01T00:05:00Z"]
    assert lr.main(args + ["--verify"]) == 1, "fixture is meant to hold over-age lines"
    assert lr.main(args + ["--once", "--quiet-seconds", "0"]) == 0
    assert lr.main(args + ["--verify"]) == 0
    assert (d / "README.txt").exists()


def test_seconds_until_daily_slot():
    now = datetime(2026, 11, 1, 0, 4, tzinfo=timezone.utc).timestamp()
    assert lr.seconds_until("00:05", now) == 60
    assert lr.seconds_until("00:05", now + 120) == DAY - 60


# ---------------------------------------------------------------- compose, host journald, CI wiring

def test_compose_uses_journald_for_every_service():
    compose = yaml.safe_load((OPS / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert {"app", "purge", "caddy", "logretention"} <= set(services)
    for name, svc in services.items():
        assert svc.get("logging", {}).get("driver") == "journald", name
        assert "max-size" not in svc["logging"].get("options", {}), name


def test_logretention_service_least_privilege():
    svc = yaml.safe_load((OPS / "docker-compose.yml").read_text(encoding="utf-8"))["services"]["logretention"]
    cmd = svc["command"]
    assert cmd[:2] == ["python", "/opt/ops/log_retention.py"] and cmd[cmd.index("--days") + 1] == "14"
    caddy_logs = [v for v in yaml.safe_load((OPS / "docker-compose.yml").read_text(encoding="utf-8"))
                  ["services"]["caddy"]["volumes"] if v.startswith("caddy_logs:")]
    assert svc["volumes"] == caddy_logs == ["caddy_logs:/var/log/caddy"]
    assert cmd[cmd.index("--dir") + 1] == "/var/log/caddy"
    assert svc["network_mode"] == "none" and svc["read_only"] is True and svc["cap_drop"] == ["ALL"]
    assert "env_file" not in svc, "no secrets in the retention container"
    docker = (OPS / "Dockerfile").read_text(encoding="utf-8")
    assert "ops/scripts/log_retention.py /opt/ops/log_retention.py" in docker


def test_journald_host_conf_has_both_limits():
    text = (OPS / "host" / "journald-belegbruecke.conf").read_text(encoding="utf-8")
    body = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert body[0] == "[Journal]"
    assert "MaxRetentionSec=14day" in body and "MaxFileSec=1day" in body


def test_ci_runs_retention_against_fixture():
    wf = yaml.safe_load((OPS / "ci" / "ci.yml").read_text(encoding="utf-8"))
    runs = "\n".join(s.get("run", "") for s in wf["jobs"]["test"]["steps"])
    assert "ops/tests/fixtures/caddy_logs" in runs
    assert "log_retention.py" in runs and "--verify" in runs and "--once" in runs


def test_runbook_documents_retention_and_install_step():
    rb = (OPS / "RUNBOOK.md").read_text(encoding="utf-8")
    sec = rb.split("## Log retention: 14 days", 1)[1].split("\n## ", 1)[0]
    for needle in ("journald-belegbruecke.conf", "/etc/systemd/journald.conf.d/", "NOT active",
                   "log_retention.py", "Cloudflare", "https://developers.cloudflare.com/", "No backups"):
        assert needle in sec, needle
