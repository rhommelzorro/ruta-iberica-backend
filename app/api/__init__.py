from flask import Blueprint

from app.api.auth import bp as auth_bp
from app.api.routes_api import bp as routes_bp
from app.api.community import bp as community_bp
from app.api.moderation import bp as moderation_bp
from app.api.health import bp as health_bp


def register_blueprints(app):
    api = Blueprint("api", __name__, url_prefix="/api")
    api.register_blueprint(health_bp)
    api.register_blueprint(auth_bp)
    api.register_blueprint(routes_bp)
    api.register_blueprint(community_bp)
    api.register_blueprint(moderation_bp)
    app.register_blueprint(api)
