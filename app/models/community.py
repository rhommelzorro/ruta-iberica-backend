from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Favorite(db.Model):
    __tablename__ = "favorites"
    __table_args__ = (
        db.UniqueConstraint("user_id", "route_id", name="uq_favorite_user_route"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="favorites")
    route = db.relationship("Route", back_populates="favorites")


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user = db.relationship("User", back_populates="comments")
    route = db.relationship("Route", back_populates="comments")

    def to_dict(self):
        return {
            "id": self.id,
            "route_id": self.route_id,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "author": {
                "id": self.user.id,
                "public_name": self.user.public_name,
            },
            "kind": "comentario_comunitario",
            "is_official": False,
        }


class Alert(db.Model):
    """Aviso comunitario (obstáculo, cierre, problema). No es información oficial."""

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    alert_type = db.Column(db.String(64), nullable=False)  # obstaculo | cierre | problema
    body = db.Column(db.Text, nullable=False)
    observed_at = db.Column(db.DateTime(timezone=True), nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="alerts")
    route = db.relationship("Route", back_populates="alerts")

    def to_dict(self):
        return {
            "id": self.id,
            "route_id": self.route_id,
            "alert_type": self.alert_type,
            "body": self.body,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "author": {
                "id": self.user.id,
                "public_name": self.user.public_name,
            },
            "kind": "aviso_comunitario",
            "is_official": False,
            "disclaimer": (
                "Aviso comunitario. No sustituye información oficial de la fuente "
                "del trazado ni confirma el estado físico actual."
            ),
        }


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_type = db.Column(db.String(32), nullable=False)  # comment | alert
    target_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), default="pending", nullable=False)
    moderator_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
