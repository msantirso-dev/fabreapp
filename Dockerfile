FROM python:3.12-slim

ARG COOLIFY_BUILD_ID=20260712-google-status-witness
ENV COOLIFY_BUILD_ID=${COOLIFY_BUILD_ID}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8002
ENV APP_PORT=8002
ENV DJANGO_SUPERUSER_USERNAME=admin
ENV DJANGO_SUPERUSER_PASSWORD=Fabregad2026!
ENV DJANGO_SUPERUSER_EMAIL=admin@fabregad.com.ar

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

EXPOSE 8002

HEALTHCHECK --interval=15s --timeout=5s --start-period=120s --retries=10 \
  CMD /bin/sh /app/scripts/healthcheck.sh

CMD ["/bin/sh", "/app/scripts/entrypoint.sh"]
