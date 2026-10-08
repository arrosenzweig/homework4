"""
Ensure the seed test account can actually log in.

The shipped database has a row for test@campuscustoms.yale.edu whose
password_hash was produced by the course fixture, in the three-part legacy
shape `pbkdf2_sha256$<salt>$<hash>`. That string does not record its iteration
count, so this app cannot reproduce the derivation and cannot verify against
it.

Rather than guess at the fixture's parameters, this script re-hashes the known
test password under the app's own scheme (see auth.py) and writes it back. The
account keeps its id, name and created_at; only the credential is replaced.

Run from the HW 4 directory:

    python backend/seed_test_user.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from auth import hash_password, verify_password

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "campus_customs.db"

TEST_EMAIL = "test@campuscustoms.yale.edu"
TEST_PASSWORD = "password"


def main() -> int:
    if not DB_PATH.exists():
        print(f"database not found at {DB_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(email) = ?", (TEST_EMAIL.lower(),)
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO users (name, email, password_hash, first_name, last_name, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                ("Test User", TEST_EMAIL, hash_password(TEST_PASSWORD), "Test", "User"),
            )
            conn.commit()
            print(f"created {TEST_EMAIL}")
            return 0

        if verify_password(TEST_PASSWORD, row["password_hash"]):
            print(f"{TEST_EMAIL} already verifies against the app's scheme; nothing to do")
            return 0

        print(f"existing hash:  {row['password_hash'][:48]}...")
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(TEST_PASSWORD), row["id"]),
        )
        conn.commit()

        check = conn.execute("SELECT password_hash FROM users WHERE id = ?", (row["id"],)).fetchone()
        ok = verify_password(TEST_PASSWORD, check["password_hash"])
        print(f"rewritten hash: {check['password_hash'][:48]}...")
        print(f"verifies: {ok}")
        return 0 if ok else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
