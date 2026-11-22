"""Registra fuentes documentadas y estado de conectores."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.services.import_routes import upsert_source


SOURCES = [
    {
        "code": "miteco_rgvp_sample",
        "name": "Red General de Vías Pecuarias (muestra)",
        "country": "ES",
        "license_name": "Reutilización información sector público (MITECO)",
        "attribution": "Fuente: © Ministerio para la Transición Ecológica y el Reto Demográfico",
        "source_url": "https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/biodiversidad/vias_pecuarias.html",
        "reuse_notes": (
            "Uso libre y gratuito citando la fuente. No desnaturalizar el sentido. "
            "Mencionar fecha de actualización cuando figure. Descarga oficial SHP/GeoJSON."
        ),
        "connector_status": "active",
    },
    {
        "code": "mapa_caminos_naturales",
        "name": "Red de Caminos Naturales (MAPA)",
        "country": "ES",
        "license_name": "Pendiente de verificación de condiciones de descarga",
        "attribution": "MAPA / Ministerio de Agricultura, Pesca y Alimentación",
        "source_url": "https://www.mapa.gob.es/es/cartografia-y-sig/ide/descargas/desarrollo-rural/red-caminos-naturales",
        "reuse_notes": "Conector pendiente: verificar licencia y formato descargable antes de importar a gran escala.",
        "connector_status": "pending",
    },
    {
        "code": "vias_verdes_ffe",
        "name": "Vías Verdes (Fundación de los Ferrocarriles Españoles)",
        "country": "ES",
        "license_name": "Sin API abierta verificada",
        "attribution": "Fundación de los Ferrocarriles Españoles — viasverdes.com",
        "source_url": "https://viasverdes.com/itinerarios/",
        "reuse_notes": (
            "La web pública no implica permiso de copia masiva. "
            "Conector pendiente hasta obtener permiso o datos abiertos autorizados."
        ),
        "connector_status": "pending",
    },
    {
        "code": "ip_ecopistas_demo",
        "name": "Ecopistas Portugal (muestra demostrativa)",
        "country": "PT",
        "license_name": "Datos de demostración — sin descarga abierta verificada en ippatrimonio.pt",
        "attribution": "Referencia informativa: IP Património / Infraestruturas de Portugal — Ecopistas",
        "source_url": "https://ippatrimonio.pt/ecopistas",
        "reuse_notes": (
            "La página institucional describe el PNE pero no ofrece GeoJSON/SHP abierto verificado. "
            "La muestra incluida está marcada is_demo=true. Conector real pendiente de permiso o datos.gov.pt."
        ),
        "connector_status": "demo",
    },
    {
        "code": "cyclin_portugal",
        "name": "Cyclin’Portugal — redes homologadas",
        "country": "PT",
        "license_name": "Pendiente",
        "attribution": "Cyclin’Portugal",
        "source_url": "https://www.cyclinportugal.pt/pt/infraestruturas/redes-de-percursos",
        "reuse_notes": "Sin API abierta verificada. Conector pendiente.",
        "connector_status": "pending",
    },
    {
        "code": "fcmp_senderos",
        "name": "FCMP — senderos homologados",
        "country": "PT",
        "license_name": "Pendiente de investigación de licencia",
        "attribution": "Federação de Campismo e Montanhismo de Portugal (a verificar)",
        "source_url": "https://www.fcmportugal.com/",
        "reuse_notes": "Investigar disponibilidad de datos abiertos y condiciones. Conector pendiente.",
        "connector_status": "pending",
    },
]


def main():
    app = create_app()
    with app.app_context():
        for s in SOURCES:
            src = upsert_source(**s)
            print(f"OK {src.code} ({src.connector_status})")


if __name__ == "__main__":
    main()
