"""Validation off the event loop with one global concurrency cap (review M1).

KoSIT starts a JVM per call, so /check and conversion jobs share one semaphore. If the engine
exposes its own semaphore or `validate_many`, those are used (checked with getattr so this works
before and after the engine change).
"""
from __future__ import annotations

import threading

MAX_PARALLEL_VALIDATIONS = 2
_APP_SEMAPHORE = threading.BoundedSemaphore(MAX_PARALLEL_VALIDATIONS)
_ENGINE_SEM_NAMES = ("VALIDATION_SEMAPHORE", "KOSIT_SEMAPHORE", "validation_semaphore", "kosit_semaphore")


def semaphore(engine=None):
    """The engine's semaphore if it has one, else the app-wide one."""
    if engine is None:
        import engine  # noqa: PLW0621
    for mod in (engine, getattr(engine, "validation", None)):
        for name in _ENGINE_SEM_NAMES:
            sem = getattr(mod, name, None) if mod is not None else None
            if sem is not None and hasattr(sem, "acquire") and hasattr(sem, "release"):
                return sem
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
