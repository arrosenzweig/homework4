"""
Password hashing and session handling for Campus Customs.

Passwords are never stored. What goes in the database is a PBKDF2-HMAC-SHA256
derivation of the password with a per-user random salt, in the same
`algorithm$salt$hash` shape the seed database already uses:

    pbkdf2_sha256$600000$<32 hex chars of salt>$<64 hex chars of hash>

Design notes:
  * PBKDF2 is deliberately slow, so guessing attempts against a stolen
    database are expensive rather than instant.
  * The salt is random per user, so two people who pick the same password
    get different hashes and one precomputed table cannot cover both.
  * Verification uses a constant-time comparison so that how long the check
    takes does not leak how much of the hash was correct.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
SALT_BYTES = 16
TOKEN_BYTES = 32

MIN_PASSWORD_LENGTH = 8
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password: str, *, iterations: int = ITERATIONS) -> str:
    """Derive a storable credential string from a plaintext password."""
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """
    Check a password against a stored credential.

    Returns False rather than raising on a malformed or unknown-format hash,
    so a bad row cannot crash the login endpoint.
    """
    try:
        parts = stored.split("$")
        if len(parts) == 4:
            algorithm, iterations_s, salt_hex, expected_hex = parts
            iterations = int(iterations_s)
            salt = bytes.fromhex(salt_hex)
        elif len(parts) == 3:
            # Legacy seed rows: pbkdf2_sha256$<salt>$<hash>, default iterations,
            # salt stored as raw text rather than hex.
            algorithm, salt_text, expected_hex = parts
            iterations = ITERATIONS
            salt = salt_text.encode("utf-8")
        else:
            return False

        if algorithm != ALGORITHM:
            return False

        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


def needs_rehash(stored: str) -> bool:
    """True if a credential was made with older parameters and should be upgraded."""
    parts = stored.split("$")
    if len(parts) != 4:
        return True
    try:
        return parts[0] != ALGORITHM or int(parts[1]) < ITERATIONS
    except ValueError:
        return True


def new_session_token() -> str:
    """A cryptographically random opaque session token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_signup(
    first_name: str, last_name: str, email: str, password: str, confirm: str
) -> str | None:
    """Return an error message, or None if the signup payload is acceptable."""
    if not first_name.strip():
        return "First name is required."
    if not last_name.strip():
        return "Last name is required."
    if not EMAIL_RE.match(email.strip()):
        return "Enter a valid email address."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if password != confirm:
        return "Passwords do not match."
    return None
