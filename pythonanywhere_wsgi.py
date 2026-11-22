"""
WSGI para PythonAnywhere (usuario: rutaiberica).

Pega este contenido en:
  Web → WSGI configuration file
  /var/www/rutaiberica_pythonanywhere_com_wsgi.py

En Web → Virtualenv usa:
  /home/rutaiberica/.virtualenvs/env
"""
import os
import sys

PROJECT = "/home/rutaiberica/ruta-iberica-backend"

if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

os.chdir(PROJECT)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT, ".env"))

from wsgi import app as application  # noqa: E402
