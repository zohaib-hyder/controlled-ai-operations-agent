import secrets

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, type=Type.ID)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(encoded: str | None, password: str) -> bool:
    try:
        valid = hasher.verify(encoded or DUMMY_HASH, password)
        return bool(encoded) and valid
    except (VerificationError, InvalidHashError):
        return False
