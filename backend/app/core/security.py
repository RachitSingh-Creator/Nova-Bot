from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenError(Exception):
    pass


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _create_token(subject: str, token_type: str, expires_minutes: int, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {"sub": subject, "type": token_type, "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    return _create_token(subject, "access", settings.access_token_expire_minutes)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    return _create_token(subject, "refresh", settings.refresh_token_expire_minutes)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise TokenError("Invalid token") from exc
    if expected_type and payload.get("type") != expected_type:
        raise TokenError("Invalid token type")
    return payload
