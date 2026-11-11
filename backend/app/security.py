"""Password hashing, agent JWTs, and webhook HMAC verification.

Password hashing uses PBKDF2 from the standard library so there is no native
build dependency (bcrypt can be painful on Windows). It is a sensible,
well-understood choice for this task.
"""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

settings = get_settings()

_PBKDF2_ROUNDS = 200_000


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


# --------------------------------------------------------------------- JWT
def create_agent_token(agent_id: str, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": agent_id,
        "username": username,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


_bearer = HTTPBearer(auto_error=False)


def require_agent(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """FastAPI dependency: returns the decoded agent token or raises 401."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        return jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


# ------------------------------------------------------------ webhook HMAC
def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Verify the `X-Signature: sha256=<hex>` header against the raw body."""
    if not signature_header:
        return False
    expected = hmac.new(
        settings.webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    provided = signature_header.strip()
    if provided.startswith("sha256="):
        provided = provided[len("sha256="):]
    return hmac.compare_digest(expected, provided)


def sign_body(raw_body: bytes) -> str:
    """Produce an `X-Signature` value — used by the Customer view path/tests."""
    digest = hmac.new(
        settings.webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return f"sha256={digest}"
