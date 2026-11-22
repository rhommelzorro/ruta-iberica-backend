from datetime import datetime, timezone

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

from app.extensions import db, limiter
from app.models import User
from app.services.mail import send_email
from app.services.security import (
    check_password,
    consume_auth_token,
    create_auth_token,
    hash_password,
    is_login_locked,
    record_login_attempt,
)

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


@bp.post("/register")
@limiter.limit("30 per hour")
def register():
    """Registro simple: correo + contraseña + confirmación. Sin verificación de correo en v1."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    password_confirm = data.get("password_confirm") or ""
    # Nombre público opcional; por defecto parte local del correo
    public_name = (data.get("public_name") or "").strip()
    if not public_name:
        public_name = (email.split("@")[0] or "Usuario")[:80]

    errors = []
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        errors.append("Correo electrónico no válido.")
    if len(password) < 8:
        errors.append("La contraseña debe tener al menos 8 caracteres.")
    if password != password_confirm:
        errors.append("La confirmación de contraseña no coincide.")
    if errors:
        return jsonify({"error": "Validación fallida", "details": errors}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Ya existe una cuenta con ese correo."}), 409

    user = User(
        email=email,
        password_hash=hash_password(password),
        public_name=public_name[:80],
        accepted_terms_at=datetime.now(timezone.utc),
        email_verified=True,  # v1: sin flujo de verificación por correo
    )
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify(
        {
            "user": user.to_public_dict(),
            "access_token": token,
            "token_type": "Bearer",
            "email_verification": {"required": False},
            "message": "Cuenta creada. Ya puede iniciar sesión.",
        }
    ), 201


@bp.get("/verify-email")
@bp.post("/verify-email")
def verify_email():
    token = request.args.get("token") or (request.get_json(silent=True) or {}).get("token")
    if not token:
        return jsonify({"error": "Falta el token."}), 400
    auth_token = consume_auth_token(token, "email_verify")
    if not auth_token:
        return jsonify(
            {
                "error": "Enlace inválido, caducado o ya utilizado.",
            }
        ), 400
    user = User.query.get(auth_token.user_id)
    if not user or not user.is_active:
        return jsonify({"error": "Usuario no encontrado."}), 404
    user.email_verified = True
    db.session.commit()
    return jsonify({"ok": True, "message": "Correo verificado correctamente."})


@bp.post("/login")
@limiter.limit("30 per hour")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if is_login_locked(
        email,
        current_app.config["LOGIN_MAX_ATTEMPTS"],
        current_app.config["LOGIN_LOCKOUT_MINUTES"],
    ):
        return jsonify(
            {
                "error": (
                    f"Demasiados intentos fallidos. Espere "
                    f"{current_app.config['LOGIN_LOCKOUT_MINUTES']} minutos."
                )
            }
        ), 429

    user = User.query.filter_by(email=email, is_active=True).first()
    if not user or user.deleted_at or not check_password(password, user.password_hash):
        record_login_attempt(email, _client_ip(), False)
        return jsonify({"error": "Credenciales incorrectas."}), 401

    record_login_attempt(email, _client_ip(), True)
    token = create_access_token(identity=str(user.id))
    return jsonify(
        {
            "access_token": token,
            "token_type": "Bearer",
            "user": user.to_public_dict(),
            "email_verified": user.email_verified,
        }
    )


@bp.post("/logout")
@jwt_required()
def logout():
    # JWT sin lista de revocación en v1: el cliente elimina el token.
    return jsonify(
        {
            "ok": True,
            "message": "Sesión cerrada en el cliente. Elimine el token de acceso localmente.",
        }
    )


@bp.post("/forgot-password")
@limiter.limit("5 per hour")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email, is_active=True).first()
    # Respuesta uniforme para no filtrar existencia de cuentas
    generic = {
        "message": (
            "Si existe una cuenta con ese correo y el servicio de correo está activo, "
            "recibirá un enlace de recuperación de un solo uso."
        )
    }
    if not user or user.deleted_at:
        return jsonify({**generic, "mail": {"sent": False, "ok": False, "message": "Sin acción."}})

    raw = create_auth_token(user.id, "password_reset", hours=2)
    link = f"{current_app.config['PUBLIC_API_URL']}/api/auth/reset-password?token={raw}"
    mail_result = send_email(
        email,
        "Recuperación de contraseña — Ruta Ibérica",
        (
            f"Hola {user.public_name},\n\n"
            f"Enlace de recuperación (válido 2 h, un solo uso):\n{link}\n\n"
            "Si no lo solicitó, ignore este mensaje.\n"
        ),
    )
    resp = {
        **generic,
        "mail": mail_result,
    }
    if not mail_result.get("sent"):
        resp["message"] = (
            "El servicio de correo no envió el enlace. "
            + mail_result.get("message", "")
        )
        # Token solo si no hubo envío real (pruebas locales / SMTP ausente)
        resp["dev_token"] = raw
        resp["dev_token_note"] = (
            "El correo NO se envió. Use este token para restablecer. No es un envío simulado."
        )
    return jsonify(resp)


@bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token") or request.args.get("token")
    password = data.get("password") or ""
    password_confirm = data.get("password_confirm") or ""
    if not token:
        return jsonify({"error": "Falta el token."}), 400
    if len(password) < 8:
        return jsonify({"error": "La contraseña debe tener al menos 8 caracteres."}), 400
    if password != password_confirm:
        return jsonify({"error": "La confirmación de contraseña no coincide."}), 400

    auth_token = consume_auth_token(token, "password_reset")
    if not auth_token:
        return jsonify({"error": "Enlace inválido, caducado o ya utilizado."}), 400

    user = User.query.get(auth_token.user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado."}), 404
    user.password_hash = hash_password(password)
    db.session.commit()
    return jsonify({"ok": True, "message": "Contraseña actualizada."})


@bp.get("/me")
@jwt_required()
def me():
    user = User.query.get(int(get_jwt_identity()))
    if not user or not user.is_active or user.deleted_at:
        return jsonify({"error": "No autorizado."}), 401
    data = user.to_public_dict()
    # El correo no se muestra en el perfil público; solo al propio usuario autenticado
    data["email"] = user.email
    return jsonify(data)


@bp.patch("/me")
@jwt_required()
def update_me():
    user = User.query.get(int(get_jwt_identity()))
    if not user or not user.is_active or user.deleted_at:
        return jsonify({"error": "No autorizado."}), 401
    data = request.get_json(silent=True) or {}
    if "public_name" in data:
        name = (data.get("public_name") or "").strip()
        if len(name) < 2:
            return jsonify({"error": "Nombre público demasiado corto."}), 400
        user.public_name = name[:80]
    db.session.commit()
    return jsonify(user.to_public_dict())


@bp.delete("/me")
@jwt_required()
def delete_me():
    """
    Eliminación de cuenta.
    Los comentarios se anonimizan (autor sustituido por cuenta de sistema) o se ocultan
    según política: aquí se conserva el texto con autor 'Cuenta eliminada' vía soft-delete
    y se desvincula el email; los comentarios quedan con user_id pero el perfil ya no es usable.
    """
    user = User.query.get(int(get_jwt_identity()))
    if not user or user.deleted_at:
        return jsonify({"error": "No autorizado."}), 401

    explanation = (
        "Su cuenta se desactivará. El correo y la contraseña dejarán de ser utilizables. "
        "Sus favoritos se eliminarán. Sus comentarios y avisos permanecerán visibles "
        "con el nombre público 'Cuenta eliminada' para conservar el historial de la ruta; "
        "no se podrán editar. Si prefiere borrarlos, elimínelos antes de borrar la cuenta."
    )

    confirm = (request.get_json(silent=True) or {}).get("confirm")
    if confirm != "ELIMINAR":
        return jsonify(
            {
                "requires_confirmation": True,
                "explanation": explanation,
                "hint": 'Envíe {"confirm":"ELIMINAR"} para confirmar.',
            }
        ), 400

    user.public_name = "Cuenta eliminada"
    user.email = f"deleted_{user.id}@invalid.local"
    user.password_hash = hash_password(secrets_token())
    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)
    # Favoritos se borran por cascade si se elimina; aquí soft-delete: limpiar favoritos
    from app.models import Favorite

    Favorite.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    return jsonify({"ok": True, "message": explanation})


def secrets_token():
    import secrets

    return secrets.token_urlsafe(24)
