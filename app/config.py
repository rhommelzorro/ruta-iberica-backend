import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-jwt-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_ACCESS_TOKEN_HOURS", "12"))
    )

    db_url = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'ruta_iberica.db').as_posix()}")
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
        rel = db_url.replace("sqlite:///", "", 1)
        # Windows: normalizar barras; rutas con espacios requieren path posix
        if not os.path.isabs(rel) and not (len(rel) > 1 and rel[1] == ":"):
            db_url = f"sqlite:///{(BASE_DIR / rel).as_posix()}"
        else:
            db_url = f"sqlite:///{Path(rel).as_posix()}"
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://127.0.0.1:5000").rstrip("/")
    APP_DEEP_LINK_BASE = os.getenv("APP_DEEP_LINK_BASE", "rutaiberica://auth")
    WEB_FALLBACK_URL = os.getenv("WEB_FALLBACK_URL", "http://127.0.0.1:5000/auth")

    MAIL_ENABLED = os.getenv("MAIL_ENABLED", "false").lower() in ("1", "true", "yes")
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER", "Ruta Iberica <noreply@ejemplo.com>"
    )

    LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
    MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))

    CORS_ORIGINS = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:8081,http://127.0.0.1:8081"
        ).split(",")
        if o.strip()
    ]

    # Península ibérica (aprox.) para validación de bbox
    MAP_BOUNDS = {
        "min_lon": -9.6,
        "min_lat": 35.9,
        "max_lon": 4.4,
        "max_lat": 43.9,
    }
