from flask import Blueprint, jsonify

from app.services.mail import mail_configured

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "app": "Ruta Iberica",
            "mail_configured": mail_configured(),
        }
    )
