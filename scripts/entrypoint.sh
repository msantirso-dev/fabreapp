#!/bin/sh
set -e

echo "Waiting for database..."
python - <<'PY'
import os, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
from django.db.utils import OperationalError

for i in range(60):
    try:
        connection.ensure_connection()
        print("Database is ready.")
        break
    except OperationalError:
        print(f"Database unavailable, retry {i+1}/60...")
        time.sleep(2)
else:
    raise SystemExit("Database not available after waiting.")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# CRÍTICO: usar el PORT que inyecta Coolify (default 3000 en Coolify).
# Si forzamos 8000 y Coolify chequea 3000 → Bad Gateway / healthcheck fail.
APP_PORT="${PORT:-3000}"
echo "Starting gunicorn on 0.0.0.0:${APP_PORT} (Coolify PORT=${PORT:-unset})"
exec gunicorn config.wsgi:application --bind "0.0.0.0:${APP_PORT}" --workers 2 --timeout 120
