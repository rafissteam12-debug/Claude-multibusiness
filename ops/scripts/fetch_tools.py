#!/usr/bin/env python3
"""Download the pinned external tools (KoSIT validator, XRechnung config, Mustang) and verify SHA-256.

Used by CI (ops/ci/ci.yml) and the Docker build (ops/Dockerfile). Stdlib only, so it runs in a
bare python:3.12-slim stage without curl/unzip. urllib honours HTTPS_PROXY.

    python ops/scripts/fetch_tools.py --dest /opt/tools [--pins ops/pins.txt] [--strict] [--env-file FILE]

Result layout:
    <dest>/kosit-validator.jar
    <dest>/kosit-config/scenarios.xml (+ resources)
    <dest>/mustang-cli.jar
With --env-file, appends KOSIT_VALIDATOR_JAR=, KOSIT_CONFIG_DIR=, MUSTANG_JAR= lines (e.g. $GITHUB_ENV).

Pin rule: a hash of "-" means "pin on first run": the hash is printed (PIN-ON-FIRST-RUN ...) and the
run continues, unless --strict. A hash that is set and does not match always fails (exit 2).
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_PINS = Path(__file__).resolve().parents[1] / "pins.txt"
KNOWN = {"kosit-validator", "kosit-config", "mustang-cli"}


def parse_pins(text: str) -> dict[str, tuple[str | None, str]]:
    """Parse pins.txt -> {name: (sha256 or None, url)}. Raises ValueError on bad lines."""
    pins: dict[str, tuple[str | None, str]] = {}
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"pins line {n}: expected '<name> <sha256|-> <url>'")
        name, sha, url = parts
        if not url.startswith("https://"):
            raise ValueError(f"pins line {n}: url must be https")
        if sha != "-" and (len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha)):
            raise ValueError(f"pins line {n}: sha256 must be 64 lowercase hex chars or '-'")
        if name in pins:
            raise ValueError(f"pins line {n}: duplicate name {name}")
        pins[name] = (None if sha == "-" else sha, url)
    missing = KNOWN - pins.keys()
    if missing:
        raise ValueError(f"pins: missing entries {sorted(missing)}")
    return pins


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, target: Path, attempts: int = 3) -> None:
    last: Exception | None = None
    for _ in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ablaufwerk-ops-fetch"})
            with urllib.request.urlopen(req, timeout=120) as r, target.open("wb") as out:
                shutil.copyfileobj(r, out)
            return
        except OSError as exc:  # URLError is an OSError
            last = exc
    raise SystemExit(f"download failed: {url} ({type(last).__name__}: {last})")


def verify(name: str, path: Path, expected: str | None, strict: bool) -> None:
    actual = sha256_file(path)
    if expected is None:
        print(f"PIN-ON-FIRST-RUN {name} {actual}")
        if strict:
            raise SystemExit(f"{name}: no pinned hash and --strict given")
        return
    if actual != expected:
        print(f"SHA-256 MISMATCH {name}: expected {expected}, got {actual}", file=sys.stderr)
        raise SystemExit(2)
    print(f"sha256 ok  {name} {actual}")


def safe_extract(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with zipfile.ZipFile(zip_path) as z:
        for member in z.infolist():
            target = (dest / member.filename).resolve()
            if root != target and root not in target.parents:
                raise SystemExit(f"zip entry escapes target dir: {member.filename}")
        z.extractall(dest)


def flatten_config(config_dir: Path) -> Path:
    """The release zip may or may not have a top folder. Move the folder that holds scenarios.xml
    up so that the result is always <config_dir>/scenarios.xml (fixed path for the Dockerfile)."""
    hits = sorted(config_dir.rglob("scenarios.xml"), key=lambda p: len(p.parts))
    if not hits:
        raise SystemExit("kosit-config: scenarios.xml not found in the release zip")
    src = hits[0].parent
    if src != config_dir:
        staging = config_dir.with_name(config_dir.name + ".tmp")
        shutil.move(str(src), staging)
        shutil.rmtree(config_dir)
        staging.rename(config_dir)
    return config_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", required=True, type=Path)
    ap.add_argument("--pins", type=Path, default=DEFAULT_PINS)
    ap.add_argument("--strict", action="store_true", help="fail when a pin is '-'")
    ap.add_argument("--env-file", type=Path, help="append KOSIT_*/MUSTANG_JAR lines to this file")
    ap.add_argument("--check-pins", action="store_true", help="only parse pins.txt, download nothing")
    args = ap.parse_args(argv)

    pins = parse_pins(args.pins.read_text(encoding="utf-8"))
    if args.check_pins:
        for name, (sha, url) in sorted(pins.items()):
            print(f"{name}: {'pinned' if sha else 'PIN-ON-FIRST-RUN'} {url}")
        return 0

    dest: Path = args.dest
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fetch-") as tmp:
        files = {}
        for name, (sha, url) in sorted(pins.items()):
            p = Path(tmp) / name
            download(url, p)
            verify(name, p, sha, args.strict)
            files[name] = p
        jar = dest / "kosit-validator.jar"
        shutil.copyfile(files["kosit-validator"], jar)
        mustang = dest / "mustang-cli.jar"
        shutil.copyfile(files["mustang-cli"], mustang)
        cfg_raw = dest / "kosit-config"
        if cfg_raw.exists():
            shutil.rmtree(cfg_raw)
        safe_extract(files["kosit-config"], cfg_raw)
    config_dir = flatten_config(cfg_raw)

    env = {"KOSIT_VALIDATOR_JAR": str(jar.resolve()), "KOSIT_CONFIG_DIR": str(config_dir.resolve()),
           "MUSTANG_JAR": str(mustang.resolve())}
    for k, v in env.items():
        print(f"{k}={v}")
    if args.env_file:
        with args.env_file.open("a", encoding="utf-8") as f:
            for k, v in env.items():
                f.write(f"{k}={v}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
