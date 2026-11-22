from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class RouteSource(db.Model):
    __tablename__ = "route_sources"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    country = db.Column(db.String(2), nullable=False)  # ES | PT
    license_name = db.Column(db.String(255), nullable=True)
    attribution = db.Column(db.Text, nullable=True)
    source_url = db.Column(db.String(512), nullable=True)
    reuse_notes = db.Column(db.Text, nullable=True)
    connector_status = db.Column(
        db.String(32), default="active", nullable=False
    )  # active | pending | demo
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    routes = db.relationship("Route", back_populates="source")


class Route(db.Model):
    """
    Distingue:
    - geometry_*: trazado publicado (no editable por usuarios)
    - usage_*: usos documentados (puede ser desconocido)
    - physical_status: estado físico documentado (puede ser desconocido)
    """

    __tablename__ = "routes"
    __table_args__ = (
        db.UniqueConstraint("source_id", "external_id", name="uq_route_source_external"),
    )

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("route_sources.id"), nullable=False)
    external_id = db.Column(db.String(128), nullable=False)

    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    country = db.Column(db.String(2), nullable=False)  # ES | PT
    locality = db.Column(db.String(255), nullable=True)

    # via_pecuaria | sendero | camino_natural | via_verde | ecopista | otra
    route_type = db.Column(db.String(64), nullable=False, default="otra")
    difficulty = db.Column(db.String(32), nullable=True)  # null = desconocido
    surface = db.Column(db.String(128), nullable=True)

    length_m = db.Column(db.Float, nullable=True)
    elevation_gain_m = db.Column(db.Float, nullable=True)

    # Usos documentados; null = desconocido. No inferir automáticamente.
    allows_walking = db.Column(db.Boolean, nullable=True)
    allows_cycling = db.Column(db.Boolean, nullable=True)
    usage_notes = db.Column(db.Text, nullable=True)
    restrictions = db.Column(db.Text, nullable=True)
    physical_status = db.Column(db.String(64), nullable=True)  # null = desconocido
    official_info = db.Column(db.Text, nullable=True)

    start_lat = db.Column(db.Float, nullable=True)
    start_lon = db.Column(db.Float, nullable=True)
    end_lat = db.Column(db.Float, nullable=True)
    end_lon = db.Column(db.Float, nullable=True)

    bbox_min_lon = db.Column(db.Float, nullable=False, index=True)
    bbox_min_lat = db.Column(db.Float, nullable=False, index=True)
    bbox_max_lon = db.Column(db.Float, nullable=False, index=True)
    bbox_max_lat = db.Column(db.Float, nullable=False, index=True)

    # GeoJSON LineString/MultiLineString como texto JSON
    geometry_detail = db.Column(db.Text, nullable=False)
    geometry_simplified = db.Column(db.Text, nullable=False)

    source_updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    license_name = db.Column(db.String(255), nullable=True)
    attribution = db.Column(db.Text, nullable=True)
    source_link = db.Column(db.String(512), nullable=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    source = db.relationship("RouteSource", back_populates="routes")
    favorites = db.relationship("Favorite", back_populates="route", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="route", cascade="all, delete-orphan")
    alerts = db.relationship("Alert", back_populates="route", cascade="all, delete-orphan")

    def to_list_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "locality": self.locality,
            "route_type": self.route_type,
            "difficulty": self.difficulty or "desconocido",
            "length_m": self.length_m,
            "elevation_gain_m": self.elevation_gain_m,
            "allows_walking": self.allows_walking,
            "allows_cycling": self.allows_cycling,
            "start_lat": self.start_lat,
            "start_lon": self.start_lon,
            "end_lat": self.end_lat,
            "end_lon": self.end_lon,
            "bbox": {
                "min_lon": self.bbox_min_lon,
                "min_lat": self.bbox_min_lat,
                "max_lon": self.bbox_max_lon,
                "max_lat": self.bbox_max_lat,
            },
            "geometry_simplified": self.geometry_simplified,
            "is_demo": self.is_demo,
            "source_code": self.source.code if self.source else None,
        }

    def to_detail_dict(self):
        data = self.to_list_dict()
        data.update(
            {
                "description": self.description,
                "surface": self.surface or "desconocido",
                "usage_notes": self.usage_notes,
                "restrictions": self.restrictions,
                "physical_status": self.physical_status or "desconocido",
                "official_info": self.official_info,
                "geometry_detail": self.geometry_detail,
                "license_name": self.license_name,
                "attribution": self.attribution,
                "source_link": self.source_link,
                "source_updated_at": (
                    self.source_updated_at.isoformat() if self.source_updated_at else None
                ),
                "source": (
                    {
                        "code": self.source.code,
                        "name": self.source.name,
                        "attribution": self.source.attribution,
                        "source_url": self.source.source_url,
                        "connector_status": self.source.connector_status,
                    }
                    if self.source
                    else None
                ),
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        )
        return data
