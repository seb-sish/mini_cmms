import hashlib
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()

def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    return _ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2 hash."""
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False

def hash_token(token: str) -> str:
    """Generate SHA-256 hex digest of an opaque token for DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_opaque_token() -> tuple[str, str]:
    """
    Generate a 32-byte cryptographically secure URL-safe opaque token,
    and return (raw_token, sha256_hex_digest).
    """
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_token(raw_token)
