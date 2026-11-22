from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Alert, Comment, Favorite, Report, Route, User

bp = Blueprint("community", __name__)


def _current_user():
    uid = get_jwt_identity()
    if not uid:
        return None
    user = User.query.get(int(uid))
    if not user or not user.is_active or user.deleted_at:
        return None
    return user


def _require_verified(user: User):
    if not user.email_verified:
        return jsonify(
            {
                "error": "Debe verificar su correo para usar favoritos, comentarios y avisos.",
            }
        ), 403
    return None


@bp.get("/routes/<int:route_id>/comments")
def list_comments(route_id: int):
    Route.query.get_or_404(route_id)
    comments = (
        Comment.query.filter_by(route_id=route_id, is_hidden=False)
        .order_by(Comment.created_at.desc())
        .all()
    )
    return jsonify(
        {
            "items": [c.to_dict() for c in comments],
            "note": "Comentarios comunitarios. No son información oficial de la fuente del trazado.",
        }
    )


@bp.post("/routes/<int:route_id>/comments")
@jwt_required()
def create_comment(route_id: int):
    user = _current_user()
    if not user:
        return jsonify({"error": "No autorizado."}), 401
    blocked = _require_verified(user)
    if blocked:
        return blocked
    Route.query.get_or_404(route_id)
    body = ((request.get_json(silent=True) or {}).get("body") or "").strip()
    if len(body) < 2 or len(body) > 2000:
        return jsonify({"error": "El comentario debe tener entre 2 y 2000 caracteres."}), 400
    c = Comment(route_id=route_id, user_id=user.id, body=body)
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


@bp.patch("/comments/<int:comment_id>")
@jwt_required()
def edit_comment(comment_id: int):
    user = _current_user()
    if not user:
        return jsonify({"error": "No autorizado."}), 401
    c = Comment.query.get_or_404(comment_id)
    if c.user_id != user.id:
        return jsonify({"error": "No puede editar comentarios ajenos."}), 403
    body = ((request.get_json(silent=True) or {}).get("body") or "").strip()
    if len(body) < 2 or len(body) > 2000:
        return jsonify({"error": "El comentario debe tener entre 2 y 2000 caracteres."}), 400
    c.body = body
    c.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(c.to_dict())


@bp.delete("/comments/<int:comment_id>")
@jwt_required()
def delete_comment(comment_id: int):
    user = _current_user()
    if not user:
        return jsonify({"error": "No autorizado."}), 401
    c = Comment.query.get_or_404(comment_id)
    if c.user_id != user.id and not (user.is_moderator or user.is_admin):
        return jsonify({"error": "No puede eliminar comentarios ajenos."}), 403
    db.session.delete(c)
    db.session.commit()
    return jsonify({"ok": True})


@bp.get("/routes/<int:route_id>/alerts")
def list_alerts(route_id: int):
    Route.query.get_or_404(route_id)
    alerts = (
        Alert.query.filter_by(route_id=route_id, is_hidden=False)
        .order_by(Alert.observed_at.desc())
        .all()
    )
    return jsonify(
        {
            "items": [a.to_dict() for a in alerts],
            "note": (
                "Avisos comunitarios. Distinga siempre de la información oficial "
                "de la fuente del trazado."
            ),
        }
    )


@bp.post("/routes/<int:route_id>/alerts")
@jwt_required()
def create_alert(route_id: int):
    user = _current_user()
    if not user:
        return jsonify({"error": "No autorizado."}), 401
    blocked = _require_verified(user)
    if blocked:
        return blocked
    Route.query.get_or_404(route_id)
    data = request.get_json(silent=True) or {}
    alert_type = (data.get("alert_type") or "").strip()
    if alert_type not in ("obstaculo", "cierre", "problema"):
        return jsonify(
            {"error": "alert_type debe ser obstaculo, cierre o problema."}
        ), 400
    body = (data.get("body") or "").strip()
    if len(body) < 2:
        return jsonify({"error": "Describa el aviso."}), 400
    try:
        observed_at = datetime.fromisoformat(data.get("observed_at"))
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return jsonify(
            {"error": "observed_at debe ser una fecha ISO 8601 (fecha de observación)."}
        ), 400

    a = Alert(
        route_id=route_id,
        user_id=user.id,
        alert_type=alert_type,
        body=body[:2000],
        observed_at=observed_at,
    )
    db.session.add(a)
    db.session.commit()
    return jsonify(a.to_dict()), 201


@bp.get("/favorites")
@jwt_required()
def list_favorites():
    user = _current_user()
    if not user:
        return jsonify({"error": "No autorizado."}), 401
    blocked = _require_verified(user)
    if blocked:
        return blocked
    favs = Favorite.query.filter_by(user_id=user.id).all()
    return jsonify(
        {
            "items": [
                {"id": f.id, "route_id": f.route_id, "route": f.route.to_list_dict()}
                for f in favs
            ]
        }
    )


@bp.post("/favorites/<int:route_id>")
@jwt_required()
def add_favorite(route_id: int):
    user = _current_user()
    if not user:
        return jsonify({"error": "No autorizado."}), 401
    blocked = _require_verified(user)
    if blocked:
        return blocked
    Route.query.get_or_404(route_id)
    existing = Favorite.query.filter_by(user_id=user.id, route_id=route_id).first()
    if existing:
        return jsonify({"ok": True, "favorite_id": existing.id})
    f = Favorite(user_id=user.id, route_id=route_id)
    db.session.add(f)
    db.session.commit()
    return jsonify({"ok": True, "favorite_id": f.id}), 201


@bp.delete("/favorites/<int:route_id>")
@jwt_required()
def remove_favorite(route_id: int):
    user = _current_user()
    if not user:
        return jsonify({"error": "No autorizado."}), 401
    f = Favorite.query.filter_by(user_id=user.id, route_id=route_id).first()
    if not f:
        return jsonify({"error": "Favorito no encontrado."}), 404
    db.session.delete(f)
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/reports")
@jwt_required()
def create_report():
    user = _current_user()
    if not user:
        return jsonify({"error": "No autorizado."}), 401
    data = request.get_json(silent=True) or {}
    target_type = data.get("target_type")
    target_id = data.get("target_id")
    reason = (data.get("reason") or "").strip()
    if target_type not in ("comment", "alert"):
        return jsonify({"error": "target_type debe ser comment o alert."}), 400
    if not target_id or len(reason) < 3:
        return jsonify({"error": "Indique target_id y un motivo."}), 400
    if target_type == "comment" and not Comment.query.get(target_id):
        return jsonify({"error": "Comentario no encontrado."}), 404
    if target_type == "alert" and not Alert.query.get(target_id):
        return jsonify({"error": "Aviso no encontrado."}), 404
    r = Report(
        reporter_id=user.id,
        target_type=target_type,
        target_id=int(target_id),
        reason=reason[:1000],
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"ok": True, "report_id": r.id}), 201
