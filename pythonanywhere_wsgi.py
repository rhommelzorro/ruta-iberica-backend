"""
WSGI para PythonAnywhere.

Copia el contenido de este archivo en:
  Web → WSGI configuration file
  (p. ej. /var/www/TUUSUARIO_pythonanywhere_com_wsgi.py)

Sustituye TUUSUARIO por tu usuario de PythonAnywhere.
"""
import os
import sys

# --- Ajusta estas dos rutas ---
PROJECT = "/home/TUUSUARIO/ruta-iberica-backend"
VENV_SITE = "/home/TUUSUARIO/ruta-iberica-backend/.venv/lib/python3.12/site-packages"
# Si usaste python3.11, cambia 3.12 → 3.11 en VENV_SITE.

if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

if os.path.isdir(VENV_SITE) and VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

# Carga .env del proyecto (además de lo que hace app.config)
from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT, ".env"))

from wsgi import app as application  # noqa: E402
