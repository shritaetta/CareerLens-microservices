from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Initialize Argon2 password hasher
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2."""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verifies a plaintext password against an Argon2 hash. Never logs password/hash."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
