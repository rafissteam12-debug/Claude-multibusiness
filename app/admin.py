"""Owner commands. Manual unsubscribe after an e-mail reply "abmelden" (legal pre-review 6.5):

    python -m app.admin unsubscribe someone@example.invalid

Removes the address from the mailing list and closes its consent record with method 'reply'. Prints only a status,
never the address. Do this on the day the reply arrives.
"""
from __future__ import annotations

import sys

from .consent import withdraw
from .db import Database
from .security import Security
from .settings import load_settings


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "unsubscribe":
        print("usage: python -m app.admin unsubscribe <e-mail>", file=sys.stderr)
        return 2
    settings = load_settings()
    db = Database(settings.database_path)
    db.migrate()
    found = withdraw(db, Security(settings, db), argv[1], method="reply")
    print("unsubscribed (method=reply)" if found else "not found: nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
