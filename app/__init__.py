from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import inspect

from app.config import Config
from app.extensions import db, jwt, limiter, migrate


def _ensure_sqlite_schema(app: Flask) -> None:
    """Si Alembic quedó 'stamped' sin tablas (p. ej. users), créalas.

    Evita HTTP 500 en registro/login por OperationalError: no such table.
    """
    uri = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
    if not str(uri).startswith("sqlite"):
        return
    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())
        if "users" in tables:
            return
        db.create_all()
        # Alinear stamp de Alembic si existe carpeta de migraciones
        try:
            from flask_migrate import stamp

            stamp(revision="head")
        except Exception:  # noqa: BLE001
            app.logger.warning("Schema creado con create_all; stamp Alembic omitido.")


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    CORS(app, origins=app.config.get("CORS_ORIGINS") or ["*"], supports_credentials=True)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    from app import models  # noqa: F401
    from app.api import register_blueprints

    register_blueprints(app)
    _ensure_sqlite_schema(app)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "No encontrado"}), 404

    @app.errorhandler(429)
    def ratelimit(e):
        return jsonify({"error": "Demasiadas peticiones. Inténtelo más tarde."}), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Error interno: %s", e)
        return jsonify(
            {
                "error": "Error interno del servidor.",
                "hint": "Si el registro falla, en backend: flask db upgrade",
            }
        ), 500

    @jwt.unauthorized_loader
    def missing_token(err):
        return jsonify({"error": "Se requiere autenticación.", "detail": err}), 401

    @jwt.invalid_token_loader
    def invalid_token(err):
        return jsonify({"error": "Token inválido.", "detail": err}), 401

    return app
