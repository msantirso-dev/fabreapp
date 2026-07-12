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

# Coolify inyecta PORT (suele ser 3000) y el proxy apunta a ese puerto.
# No forzar 8000: tiene que coincidir con el "Ports Exposes" del servicio en Coolify.
APP_PORT="${PORT:-8000}"
echo "Starting gunicorn on 0.0.0.0:${APP_PORT}"
exec gunicorn config.wsgi:application --bind "0.0.0.0:${APP_PORT}" --workers 2 --timeout 120
