"""Run the retention purge once (hourly cron): `python -m app.purge`. Prints counts only, never contents."""
from __future__ import annotations

import sys

from .db import Database
from .jobs import JobRunner
from .security import Security
from .settings import load_settings


def main() -> int:
    settings = load_settings()
    db = Database(settings.database_path)
    db.migrate()
    runner = JobRunner(settings, db, Security(settings, db), workers=1)
    try:
        counts = runner.purge()
    finally:
        runner.pool.shutdown(wait=False)
    print(f"purge: uploads={counts['uploads']} files={counts['files']} jobs={counts['jobs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
