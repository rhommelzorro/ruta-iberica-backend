"""Importación de rutas por CLI. No usar desde peticiones web para archivos pesados."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.extensions import db
from app.models import Route, RouteSource
from app.services.geo import (
    bbox_from_geometry,
    dumps_geom,
    endpoints_from_geometry,
    length_m_approx,
    parse_geojson_feature_collection,
    simplify_geometry,
    validate_wgs84_geometry,
)


def upsert_source(**kwargs) -> RouteSource:
    code = kwargs["code"]
    src = RouteSource.query.filter_by(code=code).first()
    if src is None:
        src = RouteSource(**kwargs)
        db.session.add(src)
    else:
        for k, v in kwargs.items():
            setattr(src, k, v)
    db.session.commit()
    return src


def import_feature(
    feature: dict,
    source: RouteSource,
    *,
    is_demo: bool = False,
    default_route_type: str = "otra",
) -> tuple[str, Route]:
    props = feature.get("properties") or {}
    geom = feature.get("geometry")
    if not geom:
        raise ValueError("Feature sin geometry")
    geom = validate_wgs84_geometry(geom)

    external_id = str(
        props.get("external_id")
        or props.get("id")
        or props.get("IDENT")
        or props.get("codigo")
        or props.get("CODIGO")
        or ""
    ).strip()
    if not external_id:
        # Identificador estable a partir de nombre + extremos (no por similitud de nombre solo)
        bbox = bbox_from_geometry(geom)
        external_id = f"auto-{props.get('name', props.get('nombre', 'ruta'))}-{bbox[0]:.5f}-{bbox[1]:.5f}"

    name = (
        props.get("name")
        or props.get("nombre")
        or props.get("NOMBRE")
        or props.get("Name")
        or f"Ruta {external_id}"
    )

    length = props.get("length_m")
    if length is None:
        length = length_m_approx(geom)

    # No inventar desnivel, dificultad ni permisos
    elev = props.get("elevation_gain_m")
    difficulty = props.get("difficulty")
    allows_walking = props.get("allows_walking")
    allows_cycling = props.get("allows_cycling")
    if allows_walking is not None:
        allows_walking = bool(allows_walking)
    if allows_cycling is not None:
        allows_cycling = bool(allows_cycling)

    min_lon, min_lat, max_lon, max_lat = bbox_from_geometry(geom)
    start_lat, start_lon, end_lat, end_lon = endpoints_from_geometry(geom)
    simplified = simplify_geometry(geom)

    source_updated_at = None
    if props.get("source_updated_at"):
        source_updated_at = datetime.fromisoformat(str(props["source_updated_at"]))

    route = Route.query.filter_by(source_id=source.id, external_id=external_id).first()
    action = "updated" if route else "created"
    if route is None:
        route = Route(source_id=source.id, external_id=external_id)
        db.session.add(route)

    route.name = str(name)[:255]
    route.description = props.get("description") or props.get("descripcion")
    route.country = (props.get("country") or source.country or "ES")[:2].upper()
    route.locality = props.get("locality") or props.get("localidad")
    route.route_type = props.get("route_type") or default_route_type
    route.difficulty = difficulty
    route.surface = props.get("surface")
    route.length_m = float(length) if length is not None else None
    route.elevation_gain_m = float(elev) if elev is not None else None
    route.allows_walking = allows_walking
    route.allows_cycling = allows_cycling
    route.usage_notes = props.get("usage_notes")
    route.restrictions = props.get("restrictions")
    route.physical_status = props.get("physical_status")
    route.official_info = props.get("official_info")
    route.start_lat = start_lat
    route.start_lon = start_lon
    route.end_lat = end_lat
    route.end_lon = end_lon
    route.bbox_min_lon = min_lon
    route.bbox_min_lat = min_lat
    route.bbox_max_lon = max_lon
    route.bbox_max_lat = max_lat
    route.geometry_detail = dumps_geom(geom)
    route.geometry_simplified = dumps_geom(simplified)
    route.source_updated_at = source_updated_at
    route.license_name = props.get("license_name") or source.license_name
    route.attribution = props.get("attribution") or source.attribution
    route.source_link = props.get("source_link") or source.source_url
    route.is_demo = bool(props.get("is_demo", is_demo))
    route.updated_at = datetime.now(timezone.utc)

    db.session.commit()
    return action, route


def import_geojson_file(
    path: Path,
    source_code: str,
    *,
    is_demo: bool = False,
    default_route_type: str = "otra",
    max_bytes: int = 5 * 1024 * 1024,
) -> dict:
    data = path.read_bytes()
    if len(data) > max_bytes:
        raise ValueError(f"Archivo supera el límite de {max_bytes} bytes")
    features = parse_geojson_feature_collection(data)
    source = RouteSource.query.filter_by(code=source_code).first()
    if source is None:
        raise ValueError(f"Fuente desconocida: {source_code}. Cree la fuente antes.")

    created = updated = errors = 0
    details = []
    for i, feat in enumerate(features):
        try:
            action, route = import_feature(
                feat,
                source,
                is_demo=is_demo,
                default_route_type=default_route_type,
            )
            if action == "created":
                created += 1
            else:
                updated += 1
            details.append({"index": i, "action": action, "id": route.id, "name": route.name})
        except Exception as exc:  # noqa: BLE001
            errors += 1
            details.append({"index": i, "action": "error", "error": str(exc)})

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "total_features": len(features),
        "details": details,
    }


def import_gpx_file(path: Path, source_code: str, **kwargs) -> dict:
    """Conversión mínima GPX → LineString (sin inventar metadatos)."""
    import xml.etree.ElementTree as ET

    raw = path.read_bytes()
    if len(raw) > kwargs.get("max_bytes", 5 * 1024 * 1024):
        raise ValueError("Archivo GPX demasiado grande")
    root = ET.fromstring(raw)
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    pts = []
    for trkpt in root.findall(".//g:trkpt", ns) or root.findall(".//{*}trkpt"):
        lon = float(trkpt.attrib["lon"])
        lat = float(trkpt.attrib["lat"])
        pts.append([lon, lat])
    if len(pts) < 2:
        raise ValueError("GPX sin track suficiente")
    name_el = root.find(".//g:name", ns) or root.find(".//{*}name")
    name = name_el.text if name_el is not None and name_el.text else path.stem
    feature = {
        "type": "Feature",
        "properties": {
            "external_id": f"gpx-{path.stem}",
            "name": name,
            "is_demo": kwargs.get("is_demo", False),
        },
        "geometry": {"type": "LineString", "coordinates": pts},
    }
    # Escribir temporalmente como geojson en memoria
    source = RouteSource.query.filter_by(code=source_code).first()
    if source is None:
        raise ValueError(f"Fuente desconocida: {source_code}")
    action, route = import_feature(
        feature,
        source,
        is_demo=kwargs.get("is_demo", False),
        default_route_type=kwargs.get("default_route_type", "otra"),
    )
    return {
        "created": 1 if action == "created" else 0,
        "updated": 1 if action == "updated" else 0,
        "errors": 0,
        "total_features": 1,
        "details": [{"action": action, "id": route.id, "name": route.name}],
    }
