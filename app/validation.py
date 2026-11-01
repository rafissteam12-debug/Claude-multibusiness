"""Validation off the event loop with one global concurrency cap (review M1).

/check and conversion jobs share one app-wide semaphore around every validate call (XSLT layers are
CPU-heavy too). The engine caps parallel KoSIT JVMs itself (`engine.validation.kosit_semaphore()`,
acquired inside validate/validate_many); the app deliberately does NOT acquire that one from outside,
because nesting the same bounded semaphore could deadlock. `validate_many` (one JVM per batch) is used
when the engine has it (looked up with getattr, so this also works with an older engine).
"""
from __future__ import annotations

import threading

MAX_PARALLEL_VALIDATIONS = 2
_APP_SEMAPHORE = threading.BoundedSemaphore(MAX_PARALLEL_VALIDATIONS)


def semaphore(engine=None):
    """The app-wide validation semaphore (separate from the engine's internal KoSIT semaphore)."""
    return _APP_SEMAPHORE


def _validate_many_fn(engine):
    fn = getattr(engine, "validate_many", None)
    if fn is None:
        fn = getattr(getattr(engine, "validation", None), "validate_many", None)
    return fn if callable(fn) else None


def validate_one(data: bytes, filename: str, engine=None) -> dict:
    if engine is None:
        import engine  # noqa: PLW0621
    with semaphore(engine):
        return engine.validate(data, filename)


def validate_batch(items: list[tuple[bytes, str]], engine=None) -> list[dict]:
    """Validate several files; one engine batch call when `validate_many` exists, else one by one."""
    if engine is None:
        import engine  # noqa: PLW0621
    if not items:
        return []
    fn = _validate_many_fn(engine)
    if fn is not None:
        with semaphore(engine):
            try:
                reports = list(fn(items))
            except TypeError:  # other signature: list of bytes
                reports = None
            if reports is None:
                try:
                    reports = list(fn([d for d, _ in items]))
                except TypeError:
                    reports = None
        if reports is not None and len(reports) == len(items) and all(isinstance(r, dict) for r in reports):
            return reports
    return [validate_one(d, n, engine) for d, n in items]
