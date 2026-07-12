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

# Crear superusuario si está definido por env (Coolify).
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  echo "Ensuring superuser ${DJANGO_SUPERUSER_USERNAME} exists..."
  python - <<'PY'
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"]
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@fabregad.com.ar")
user, created = User.objects.get_or_create(
    username=username,
    defaults={"email": email, "is_staff": True, "is_superuser": True},
)
user.email = email
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()
print("Superuser created." if created else "Superuser updated.")
PY
fi

# Puerto fijo pedido: 8002 (Coolify Ports Exposes debe ser 8002).
APP_PORT="${APP_PORT:-8002}"
export PORT="${APP_PORT}"
echo "Starting gunicorn on 0.0.0.0:${APP_PORT}"
exec gunicorn config.wsgi:application --bind "0.0.0.0:${APP_PORT}" --workers 2 --timeout 120
