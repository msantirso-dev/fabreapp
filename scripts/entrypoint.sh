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

# Puerto fijo pedido: 8002 (Coolify Ports Exposes debe ser 8002).
APP_PORT="${APP_PORT:-8002}"
export PORT="${APP_PORT}"
echo "Starting gunicorn on 0.0.0.0:${APP_PORT}"
exec gunicorn config.wsgi:application --bind "0.0.0.0:${APP_PORT}" --workers 2 --timeout 120
