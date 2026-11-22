import smtplib
from email.message import EmailMessage

from flask import current_app


def mail_configured() -> bool:
    cfg = current_app.config
    return bool(
        cfg.get("MAIL_ENABLED")
        and cfg.get("MAIL_SERVER")
        and cfg.get("MAIL_DEFAULT_SENDER")
    )


def send_email(to_address: str, subject: str, body: str) -> dict:
    """
    Intenta enviar correo. Nunca simula éxito si el servicio no está configurado.
    Devuelve {ok, sent, message}.
    """
    if not mail_configured():
        return {
            "ok": False,
            "sent": False,
            "message": (
                "El servicio de correo no está configurado. "
                "Active MAIL_ENABLED y complete MAIL_SERVER, MAIL_USERNAME, "
                "MAIL_PASSWORD y MAIL_DEFAULT_SENDER. El mensaje NO se ha enviado."
            ),
        }

    cfg = current_app.config
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["MAIL_DEFAULT_SENDER"]
    msg["To"] = to_address
    msg.set_content(body)

    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=20) as smtp:
            if cfg.get("MAIL_USE_TLS"):
                smtp.starttls()
            if cfg.get("MAIL_USERNAME"):
                smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            smtp.send_message(msg)
        return {"ok": True, "sent": True, "message": "Correo enviado."}
    except Exception as exc:  # noqa: BLE001 — devolver error claro a la API
        return {
            "ok": False,
            "sent": False,
            "message": f"Error al enviar el correo: {exc}. El mensaje NO se ha enviado.",
        }
