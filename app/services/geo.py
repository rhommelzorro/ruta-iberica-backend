"""Utilidades de geometría sin PostGIS. Coordenadas WGS84 (EPSG:4326)."""

from __future__ import annotations

import json
import math
from typing import Any

try:
    from shapely.geometry import shape, mapping
    from shapely.ops import transform as shapely_transform
    from shapely.validation import explain_validity

    HAS_SHAPELY = True
except ImportError:  # pragma: no cover
    HAS_SHAPELY = False


def _coords_from_geometry(geom: dict) -> list[list[float]]:
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not gtype or coords is None:
        raise ValueError("Geometría sin type o coordinates")
    points: list[list[float]] = []
    if gtype == "LineString":
        points = coords
    elif gtype == "MultiLineString":
        for line in coords:
            points.extend(line)
    elif gtype == "Point":
        points = [coords]
    else:
        raise ValueError(f"Tipo de geometría no soportado: {gtype}")
    return points


def validate_wgs84_geometry(geom: dict) -> dict:
    if not isinstance(geom, dict) or "type" not in geom or "coordinates" not in geom:
        raise ValueError("GeoJSON Geometry inválido")
    points = _coords_from_geometry(geom)
    if len(points) < 2 and geom["type"] != "Point":
        raise ValueError("La línea debe tener al menos 2 puntos")
    for p in points:
        if len(p) < 2:
            raise ValueError("Coordenada incompleta")
        lon, lat = float(p[0]), float(p[1])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError(f"Coordenada fuera de WGS84: {lon},{lat}")
    if HAS_SHAPELY:
        g = shape(geom)
        if not g.is_valid:
            raise ValueError(f"Geometría inválida: {explain_validity(g)}")
        if g.is_empty:
            raise ValueError("Geometría vacía")
    return geom


def bbox_from_geometry(geom: dict) -> tuple[float, float, float, float]:
    points = _coords_from_geometry(geom)
    lons = [float(p[0]) for p in points]
    lats = [float(p[1]) for p in points]
    return min(lons), min(lats), max(lons), max(lats)


def endpoints_from_geometry(geom: dict) -> tuple[float, float, float, float]:
    points = _coords_from_geometry(geom)
    start = points[0]
    end = points[-1]
    return float(start[1]), float(start[0]), float(end[1]), float(end[0])


def simplify_geometry(geom: dict, tolerance: float = 0.00015) -> dict:
    """Simplifica para vista general. Sin shapely: muestrea puntos."""
    if HAS_SHAPELY:
        g = shape(geom)
        simplified = g.simplify(tolerance, preserve_topology=True)
        return mapping(simplified)

    def sample_line(line: list, step: int = 3) -> list:
        if len(line) <= 4:
            return line
        out = line[::step]
        if out[-1] != line[-1]:
            out.append(line[-1])
        return out

    gtype = geom["type"]
    if gtype == "LineString":
        return {"type": "LineString", "coordinates": sample_line(geom["coordinates"])}
    if gtype == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [sample_line(line) for line in geom["coordinates"]],
        }
    return geom


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def length_m_approx(geom: dict) -> float | None:
    try:
        points = _coords_from_geometry(geom)
        total = 0.0
        for i in range(1, len(points)):
            lon1, lat1 = float(points[i - 1][0]), float(points[i - 1][1])
            lon2, lat2 = float(points[i][0]), float(points[i][1])
            total += haversine_m(lat1, lon1, lat2, lon2)
        return total
    except Exception:
        return None


def parse_geojson_feature_collection(raw: str | bytes | dict) -> list[dict[str, Any]]:
    if isinstance(raw, (str, bytes)):
        data = json.loads(raw)
    else:
        data = raw
    if data.get("type") == "FeatureCollection":
        return data.get("features") or []
    if data.get("type") == "Feature":
        return [data]
    if data.get("type") in ("LineString", "MultiLineString"):
        return [{"type": "Feature", "properties": {}, "geometry": data}]
    raise ValueError("Se espera FeatureCollection, Feature o LineString/MultiLineString")


def dumps_geom(geom: dict) -> str:
    return json.dumps(geom, separators=(",", ":"))
