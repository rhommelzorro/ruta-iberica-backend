import json
import math

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_

from app.extensions import db
from app.models import Route
from app.services.geo import haversine_m

bp = Blueprint("routes", __name__, url_prefix="/routes")


def _parse_bool(val):
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("1", "true", "yes", "si", "sí")


@bp.get("")
def list_routes():
    """Consulta por bbox visible + filtros + paginación. No descarga toda la península."""
    try:
        min_lon = float(request.args["min_lon"])
        min_lat = float(request.args["min_lat"])
        max_lon = float(request.args["max_lon"])
        max_lat = float(request.args["max_lat"])
    except (KeyError, ValueError):
        return jsonify(
            {
                "error": "Parámetros bbox obligatorios: min_lon, min_lat, max_lon, max_lat",
            }
        ), 400

    if min_lon >= max_lon or min_lat >= max_lat:
        return jsonify({"error": "Bbox inválido"}), 400

    # Limitar tamaño de bbox para evitar consultas excesivas
    if (max_lon - min_lon) > 8 or (max_lat - min_lat) > 8:
        return jsonify(
            {
                "error": "El área solicitada es demasiado grande. Acerque el mapa.",
            }
        ), 400

    q = Route.query.filter(
        Route.bbox_max_lon >= min_lon,
        Route.bbox_min_lon <= max_lon,
        Route.bbox_max_lat >= min_lat,
        Route.bbox_min_lat <= max_lat,
    )

    country = request.args.get("country")
    if country:
        q = q.filter(Route.country == country.upper())

    route_type = request.args.get("route_type")
    if route_type:
        q = q.filter(Route.route_type == route_type)

    difficulty = request.args.get("difficulty")
    if difficulty and difficulty != "desconocido":
        q = q.filter(Route.difficulty == difficulty)

    min_length = request.args.get("min_length_m", type=float)
    max_length = request.args.get("max_length_m", type=float)
    if min_length is not None:
        q = q.filter(Route.length_m >= min_length)
    if max_length is not None:
        q = q.filter(Route.length_m <= max_length)

    walking = _parse_bool(request.args.get("allows_walking"))
    cycling = _parse_bool(request.args.get("allows_cycling"))
    if walking is True:
        q = q.filter(Route.allows_walking.is_(True))
    if cycling is True:
        q = q.filter(Route.allows_cycling.is_(True))

    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Route.name.ilike(like), Route.locality.ilike(like)))

    near_lat = request.args.get("near_lat", type=float)
    near_lon = request.args.get("near_lon", type=float)
    near_radius_m = request.args.get("near_radius_m", type=float, default=50000)

    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, max(1, request.args.get("per_page", 20, type=int)))

    routes = q.all()

    if near_lat is not None and near_lon is not None:
        scored = []
        for r in routes:
            if r.start_lat is None or r.start_lon is None:
                continue
            d = haversine_m(near_lat, near_lon, r.start_lat, r.start_lon)
            if d <= near_radius_m:
                scored.append((d, r))
        scored.sort(key=lambda x: x[0])
        total = len(scored)
        start = (page - 1) * per_page
        page_items = scored[start : start + per_page]
        items = []
        for d, r in page_items:
            item = r.to_list_dict()
            item["distance_to_start_m"] = round(d)
            # Distancia de viaje desconocida: no inventar
            item["travel_distance_m"] = None
            item["travel_distance_note"] = (
                "Distancia de viaje no calculada. Use una app de navegación externa."
            )
            items.append(item)
    else:
        total = len(routes)
        start = (page - 1) * per_page
        page_routes = routes[start : start + per_page]
        items = []
        for r in page_routes:
            item = r.to_list_dict()
            # Parse geometry string for clients that expect object
            try:
                item["geometry_simplified"] = json.loads(r.geometry_simplified)
            except json.JSONDecodeError:
                pass
            items.append(item)

    # Asegurar geometry como objeto en todos los casos
    for item in items:
        g = item.get("geometry_simplified")
        if isinstance(g, str):
            try:
                item["geometry_simplified"] = json.loads(g)
            except json.JSONDecodeError:
                item["geometry_simplified"] = None

    return jsonify(
        {
            "items": items,
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": max(1, math.ceil(total / per_page)) if total else 0,
        }
    )


@bp.get("/<int:route_id>")
def route_detail(route_id: int):
    route = Route.query.get_or_404(route_id)
    data = route.to_detail_dict()
    for key in ("geometry_detail", "geometry_simplified"):
        val = data.get(key)
        if isinstance(val, str):
            try:
                data[key] = json.loads(val)
            except json.JSONDecodeError:
                data[key] = None
    return jsonify(data)


@bp.get("/<int:route_id>/access")
def route_access(route_id: int):
    """Coordenadas del inicio confirmado para navegación externa. Sin aparcamientos inventados."""
    route = Route.query.get_or_404(route_id)
    if route.start_lat is None or route.start_lon is None:
        return jsonify(
            {
                "error": "Esta ruta no tiene punto de inicio confirmado en los datos.",
                "start": None,
            }
        ), 404

    user_lat = request.args.get("user_lat", type=float)
    user_lon = request.args.get("user_lon", type=float)
    straight = None
    if user_lat is not None and user_lon is not None:
        straight = round(
            haversine_m(user_lat, user_lon, route.start_lat, route.start_lon)
        )

    # Enlaces a apps externas (sin servicios de pago adicionales)
    lat, lon = route.start_lat, route.start_lon
    return jsonify(
        {
            "start": {"lat": lat, "lon": lon},
            "end": (
                {"lat": route.end_lat, "lon": route.end_lon}
                if route.end_lat is not None
                else None
            ),
            "straight_line_distance_m": straight,
            "travel_distance_m": None,
            "travel_distance_note": (
                "La distancia de viaje (por carretera) no se calcula en esta versión. "
                "Ábrala en una aplicación de navegación externa."
            ),
            "navigation": {
                "google_maps": f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}",
                "geo_uri": f"geo:{lat},{lon}?q={lat},{lon}({route.name})",
                "apple_maps": f"http://maps.apple.com/?daddr={lat},{lon}",
            },
            "note": (
                "Solo se indica el acceso confirmado por el trazado publicado. "
                "No se inventan aparcamientos ni puntos de acceso adicionales."
            ),
        }
    )
