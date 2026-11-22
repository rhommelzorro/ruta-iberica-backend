"""Punto de entrada WSGI para PythonAnywhere y gunicorn."""
from app import create_app

app = create_app()
application = app  # nombre que espera PythonAnywhere