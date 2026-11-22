from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Alert, Comment, Report, User

bp = Blueprint("moderation", __name__, url_prefix="/moderation")


def _moderator():
    user = User.query.get(int(get_jwt_identity()))
    if not user or not user.is_active or user.deleted_at:
        return None
    if not (user.is_moderator or user.is_admin):
        return None
    return user


@bp.get("/reports")
@jwt_required()
def list_reports():
    mod = _moderator()
    if not mod:
        return jsonify({"error": "Se requieren privilegios de moderación."}), 403
    status = request.args.get("status", "pending")
    q = Report.query
    if status:
        q = q.filter_by(status=status)
    items = q.order_by(Report.created_at.desc()).limit(100).all()
    return jsonify(
        {
            "items": [
                {
                    "id": r.id,
                    "target_type": r.target_type,
                    "target_id": r.target_id,
                    "reason": r.reason,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "moderator_note": r.moderator_note,
                }
                for r in items
            ]
        }
    )


@bp.post("/reports/<int:report_id>/resolve")
@jwt_required()
def resolve_report(report_id: int):
    mod = _moderator()
    if not mod:
        return jsonify({"error": "Se requieren privilegios de moderación."}), 403
    report = Report.query.get_or_404(report_id)
    data = request.get_json(silent=True) or {}
    action = data.get("action")  # hide | dismiss
    note = (data.get("note") or "").strip()
    if action not in ("hide", "dismiss"):
        return jsonify({"error": "action debe ser hide o dismiss."}), 400

    if action == "hide":
        if report.target_type == "comment":
            c = Comment.query.get(report.target_id)
            if c:
                c.is_hidden = True
        elif report.target_type == "alert":
            a = Alert.query.get(report.target_id)
            if a:
                a.is_hidden = True
        report.status = "resolved_hidden"
    else:
        report.status = "dismissed"

    report.moderator_note = note or None
    report.resolved_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"ok": True, "status": report.status})
