# Ruta Ibérica — Backend

API Flask + SQLite + migraciones Alembic para rutas de bicicleta y senderismo en España y Portugal peninsulares.

Frontend (Expo): [ruta-iberica](https://github.com/rhommelzorro/ruta-iberica)

## Requisitos

- Python 3.11–3.13 recomendado
- SMTP opcional para correo

## Arranque local

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
set FLASK_APP=wsgi.py
flask db upgrade
python scripts/seed_sources.py
python scripts/import_geojson.py --file data/samples/es_via_pecuaria_sample.geojson --source miteco_rgvp_sample --type via_pecuaria --demo
python scripts/import_geojson.py --file data/samples/pt_ecopista_demo.geojson --source ip_ecopistas_demo --type ecopista --demo
flask run
```

API: `http://127.0.0.1:5000/api/health`

El archivo `.env` **no** se sube a GitHub. En PythonAnywhere se crea en el servidor a partir de `.env.example`.

## Pruebas

```bash
.\.venv\Scripts\pytest -q
```

## Documentación

- `docs/DESPLIEGUE.md` — PythonAnywhere
- `docs/FUENTES.md` — conectores y licencias
