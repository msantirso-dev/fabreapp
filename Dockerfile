FROM python:3.12-slim

# Change this value whenever Coolify skips the build incorrectly.
ARG COOLIFY_BUILD_ID=20260712-hc8000-v2
ENV COOLIFY_BUILD_ID=${COOLIFY_BUILD_ID}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV APP_PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN sed -i 's/\r$//' /app/scripts/entrypoint.sh \
    && chmod +x /app/scripts/entrypoint.sh \
    && SECRET_KEY=build-only DEBUG=False ALLOWED_HOSTS=* \
       python manage.py collectstatic --noinput

EXPOSE 8000

# Debe coincidir con gunicorn (APP_PORT=8000).
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=8 \
  CMD curl -f http://127.0.0.1:8000/accounts/login/ || exit 1

CMD ["/bin/sh", "/app/scripts/entrypoint.sh"]
