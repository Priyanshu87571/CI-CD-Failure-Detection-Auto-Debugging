import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from backend.app.core.config import settings

# Argon2id password hasher with modern secure parameters
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16
)


def get_password_hash(password: str) -> str:
    """Hash password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "nbf": now
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        decoded_payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return decoded_payload
    except jwt.PyJWTError:
        return None


def verify_github_signature(payload_body: bytes, signature_header: Optional[str], secret: str) -> bool:
    """
    Verify GitHub webhook signature using HMAC-SHA256 in constant time.
    Format: sha256=<hex_digest>
    """
    if not signature_header or not secret:
        return False
    
    parts = signature_header.split("=", 1)
    if len(parts) != 2 or parts[0] != "sha256":
        return False
    
    expected_hash = parts[1]
    mac = hmac.new(secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
    computed_hash = mac.hexdigest()
    
    return hmac.compare_digest(computed_hash, expected_hash)
