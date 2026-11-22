"""
Importación CLI de GeoJSON/GPX.

Uso:
  python scripts/import_geojson.py --file ../data/samples/es_via_pecuaria_sample.geojson \\
      --source miteco_rgvp_sample --type via_pecuaria

  python scripts/import_geojson.py --file ruta.gpx --source miteco_rgvp_sample --format gpx
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.services.import_routes import import_geojson_file, import_gpx_file


def main():
    parser = argparse.ArgumentParser(description="Importar rutas GeoJSON/GPX")
    parser.add_argument("--file", required=True, help="Ruta al archivo")
    parser.add_argument("--source", required=True, help="Código de fuente")
    parser.add_argument("--type", default="otra", help="Tipo de ruta por defecto")
    parser.add_argument("--demo", action="store_true", help="Marcar como demostración")
    parser.add_argument("--format", choices=["geojson", "gpx", "auto"], default="auto")
    parser.add_argument("--max-bytes", type=int, default=5 * 1024 * 1024)
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"No existe: {path}", file=sys.stderr)
        sys.exit(1)

    fmt = args.format
    if fmt == "auto":
        fmt = "gpx" if path.suffix.lower() == ".gpx" else "geojson"

    app = create_app()
    with app.app_context():
        if fmt == "gpx":
            result = import_gpx_file(
                path,
                args.source,
                is_demo=args.demo,
                default_route_type=args.type,
                max_bytes=args.max_bytes,
            )
        else:
            result = import_geojson_file(
                path,
                args.source,
                is_demo=args.demo,
                default_route_type=args.type,
                max_bytes=args.max_bytes,
            )
        print(result)


if __name__ == "__main__":
    main()
