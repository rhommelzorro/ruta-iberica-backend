from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    public_name = db.Column(db.String(80), nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    accepted_terms_at = db.Column(db.DateTime(timezone=True), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_moderator = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    favorites = db.relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="user")
    alerts = db.relationship("Alert", back_populates="user")

    def to_public_dict(self):
        return {
            "id": self.id,
            "public_name": self.public_name,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_moderator": self.is_moderator,
        }


class AuthToken(db.Model):
    """Tokens de un solo uso: verificación de correo o recuperación de contraseña."""

    __tablename__ = "auth_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    purpose = db.Column(db.String(32), nullable=False)  # email_verify | password_reset
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User")


class LoginAttempt(db.Model):
    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=True)
    success = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
