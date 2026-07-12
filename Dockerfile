FROM python:3.12-slim

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

# Coolify gestiona el healthcheck (path /accounts/login/, port 8000).
# No definir HEALTHCHECK aquí: evita desfasajes de puerto (3000 vs 8000).

CMD ["/bin/sh", "/app/scripts/entrypoint.sh"]
