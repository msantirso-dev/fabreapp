FROM python:3.12-slim

ARG COOLIFY_BUILD_ID=20260712-respect-coolify-port
ENV COOLIFY_BUILD_ID=${COOLIFY_BUILD_ID}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Coolify sobrescribe PORT en runtime; 3000 es el default típico de Coolify.
ENV PORT=3000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN sed -i 's/\r$//' /app/scripts/entrypoint.sh /app/scripts/healthcheck.sh \
    && chmod +x /app/scripts/entrypoint.sh /app/scripts/healthcheck.sh \
    && SECRET_KEY=build-only DEBUG=False ALLOWED_HOSTS=* \
       python manage.py collectstatic --noinput

EXPOSE 3000 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=120s --retries=10 \
  CMD /bin/sh /app/scripts/healthcheck.sh

CMD ["/bin/sh", "/app/scripts/entrypoint.sh"]
