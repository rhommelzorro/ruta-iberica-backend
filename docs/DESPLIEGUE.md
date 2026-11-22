# Despliegue

## Backend en PythonAnywhere

### Requisitos según plan

| Capacidad | Plan gratuito / limitaciones | Plan de pago |
|---|---|---|
| SQLite | Disponible (más lento en nube; OK para v1) | Disponible |
| MySQL | Depende de la fecha de creación de la cuenta (cambios 2026) | Disponible |
| Postgres | No en gratuito; add-on de pago | Disponible (sin PostGIS verificado) |
| Procesos permanentes | **No** (workers/celery no) | Workers limitados según plan |
| Internet saliente | Restringido en gratuito (whitelist) | Completo |
| SMTP externo | Puede fallar en gratuito | Más fiable |

**Esta app:** Flask + SQLite + CLI de importación (sin procesos permanentes ni PostGIS). Compatible con cuenta gratuita para pruebas; para correo y tráfico real conviene plan de pago.

### Pasos

1. Suba este repositorio (p. ej. `~/ruta-iberica-backend`).
2. Cree un virtualenv con **Python 3.11, 3.12 o 3.13** (imagen *innit*):
   ```bash
   mkvirtualenv --python=python3.12 rutaiberica
   pip install -r requirements.txt
   ```
3. Copie `.env.example` → `.env` y configure `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL` (ruta absoluta a SQLite), `PUBLIC_API_URL`, correo si aplica.
4. Migraciones:
   ```bash
   export FLASK_APP=wsgi.py
   flask db upgrade
   python scripts/seed_sources.py
   python scripts/import_geojson.py --file data/samples/es_via_pecuaria_sample.geojson --source miteco_rgvp_sample --type via_pecuaria --demo
   python scripts/import_geojson.py --file data/samples/pt_ecopista_demo.geojson --source ip_ecopistas_demo --type ecopista --demo
   ```
5. Web app WSGI (ejemplo):
   ```python
   import sys
   path = '/home/USUARIO/ruta-iberica-backend'
   if path not in sys.path:
       sys.path.append(path)
   from wsgi import app as application
   ```
6. Recargue la web app tras cambios.
7. **No** ejecute importaciones pesadas dentro de peticiones HTTP; use la consola Bash.

### Copias de seguridad

- SQLite: copie el fichero `.db` con la web app detenida o en modo lectura.
- Alternativa: `sqlite3 ruta_iberica.db ".backup 'backup.db'"`.
- Guarde también `.env` fuera del repositorio y el historial de migraciones `migrations/`.

### Migraciones

```bash
flask db migrate -m "descripcion"
flask db upgrade
```

En producción: haga backup antes de `upgrade`.

---

## App Android (APK)

1. Configure Google Maps (`docs/GOOGLE_MAPS.md`).
2. En ``.env` del frontend`: `EXPO_PUBLIC_API_URL=https://USUARIO.pythonanywhere.com`.
3. Development build / APK con EAS:
   ```bash
   cd ruta-iberica  # repo frontend
   npx eas-cli login
   npx eas build -p android --profile preview
   ```
4. O local tras prebuild:
   ```bash
   npx expo prebuild -p android
   cd android && ./gradlew assembleRelease
   ```

**No** se genera ni se sube una APK en este repositorio de forma automática.

---

## Correo

Sin `MAIL_ENABLED=true` y SMTP válido, la API **no simula** envíos: responde que el correo no se ha enviado. En `DEBUG` puede devolver `dev_token` solo para pruebas locales.
