import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

from app.extensions import db
from app.models import AuthToken, LoginAttempt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_raw_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_auth_token(user_id: int, purpose: str, hours: int = 24) -> str:
    raw = generate_raw_token()
    token = AuthToken(
        user_id=user_id,
        token_hash=hash_token(raw),
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
    )
    db.session.add(token)
    db.session.commit()
    return raw


def consume_auth_token(raw_token: str, purpose: str):
    """Devuelve el AuthToken válido o None. Marca como usado (un solo uso)."""
    th = hash_token(raw_token)
    token = AuthToken.query.filter_by(token_hash=th, purpose=purpose).first()
    if not token:
        return None
    now = datetime.now(timezone.utc)
    expires = token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if token.used_at is not None:
        return None
    if expires < now:
        return None
    token.used_at = now
    db.session.commit()
    return token


def record_login_attempt(email: str, ip_address: str | None, success: bool):
    db.session.add(
        LoginAttempt(email=email.lower().strip(), ip_address=ip_address, success=success)
    )
    db.session.commit()


def is_login_locked(email: str, max_attempts: int, lockout_minutes: int) -> bool:
    since = datetime.now(timezone.utc) - timedelta(minutes=lockout_minutes)
    q = (
        LoginAttempt.query.filter(
            LoginAttempt.email == email.lower().strip(),
            LoginAttempt.created_at >= since,
        )
        .order_by(LoginAttempt.created_at.desc())
        .limit(max_attempts)
        .all()
    )
    if len(q) < max_attempts:
        return False
    return all(not a.success for a in q)
