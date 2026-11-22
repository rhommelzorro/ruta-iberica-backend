import pytest

from app import create_app
from app.extensions import db
from app.services.import_routes import upsert_source, import_feature


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "DEBUG": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "MAIL_ENABLED": False,
            "JWT_SECRET_KEY": "test-jwt",
            "SECRET_KEY": "test-secret",
        }
    )
    with app.app_context():
        db.create_all()
        upsert_source(
            code="test_src",
            name="Test",
            country="ES",
            license_name="test",
            attribution="test",
            source_url="https://example.com",
            reuse_notes="test",
            connector_status="demo",
        )
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _seed_route(app):
    with app.app_context():
        from app.models import RouteSource

        src = RouteSource.query.filter_by(code="test_src").first()
        import_feature(
            {
                "type": "Feature",
                "properties": {
                    "external_id": "R1",
                    "name": "Ruta Test",
                    "country": "ES",
                    "locality": "Madrid",
                    "route_type": "via_pecuaria",
                    "is_demo": True,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-3.7, 40.4], [-3.69, 40.41], [-3.68, 40.42]],
                },
            },
            src,
            is_demo=True,
            default_route_type="via_pecuaria",
        )


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["mail_configured"] is False


def test_register_simple_no_verification(client, app):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "a@example.com",
            "password": "secreto123",
            "password_confirm": "secreto123",
        },
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["email_verification"]["required"] is False
    assert data["access_token"]
    assert data["user"]["email_verified"] is True


def test_login_lockout(client, app):
    client.post(
        "/api/auth/register",
        json={
            "email": "b@example.com",
            "password": "secreto123",
            "password_confirm": "secreto123",
        },
    )
    for _ in range(5):
        client.post(
            "/api/auth/login",
            json={"email": "b@example.com", "password": "mala"},
        )
    locked = client.post(
        "/api/auth/login",
        json={"email": "b@example.com", "password": "secreto123"},
    )
    assert locked.status_code == 429


def test_routes_bbox_and_unauthorized_favorite(client, app):
    _seed_route(app)
    r = client.get(
        "/api/routes",
        query_string={
            "min_lon": -4,
            "min_lat": 40,
            "max_lon": -3,
            "max_lat": 41,
        },
    )
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert len(items) >= 1
    route_id = items[0]["id"]

    fav = client.post(f"/api/favorites/{route_id}")
    assert fav.status_code == 401


def test_reimport_no_duplicate(app):
    with app.app_context():
        from app.models import Route, RouteSource

        src = RouteSource.query.filter_by(code="test_src").first()
        feat = {
            "type": "Feature",
            "properties": {"external_id": "DUP1", "name": "Dup", "country": "ES"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[-3.7, 40.4], [-3.69, 40.41]],
            },
        }
        a1, _ = import_feature(feat, src)
        a2, _ = import_feature(feat, src)
        assert a1 == "created"
        assert a2 == "updated"
        assert Route.query.filter_by(external_id="DUP1").count() == 1


def test_invalid_geometry_rejected(app):
    with app.app_context():
        from app.models import RouteSource
        from app.services.geo import validate_wgs84_geometry
        import pytest as pt

        with pt.raises(ValueError):
            validate_wgs84_geometry(
                {"type": "LineString", "coordinates": [[999, 40], [3, 40]]}
            )


def test_password_reset_single_use(client, app):
    client.post(
        "/api/auth/register",
        json={
            "email": "c@example.com",
            "password": "secreto123",
            "password_confirm": "secreto123",
        },
    )
    forgot = client.post("/api/auth/forgot-password", json={"email": "c@example.com"})
    token = forgot.get_json().get("dev_token")
    assert token
    ok = client.post(
        "/api/auth/reset-password",
        json={
            "token": token,
            "password": "nueva12345",
            "password_confirm": "nueva12345",
        },
    )
    assert ok.status_code == 200
    again = client.post(
        "/api/auth/reset-password",
        json={
            "token": token,
            "password": "otra12345",
            "password_confirm": "otra12345",
        },
    )
    assert again.status_code == 400
