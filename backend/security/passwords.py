"""Argon2id password hashing.

Argon2id is the OWASP-recommended default for new applications. Plaintext
passwords are never stored, logged, or returned by the API.
"""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

# OWASP "second recommended" Argon2id parameters: 19 MiB memory, 2 iterations,
# 1 degree of parallelism. Comfortable on a Render free/starter instance.
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19 * 1024,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

# A pre-computed hash used to equalise response time when an email does not
# exist, so login timing cannot be used to enumerate accounts.
_DUMMY_HASH = _hasher.hash("synapse-timing-equaliser")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError, TypeError, ValueError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, TypeError, ValueError):
        return True


def dummy_verify() -> None:
    """Burn roughly one hash verification worth of CPU time."""
    try:
        _hasher.verify(_DUMMY_HASH, "not-the-password")
    except Exception:
        pass
