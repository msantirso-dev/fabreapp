# Fabrenaque (fabreapp)

Sistema para estudio contable (cliente externo, dominio fabregad.com.ar): vencimientos fiscales con finalización colaborativa y un único calendario de Google compartido. Alias: "Fabrenaque" (`APPLICATION_NAME=fabrenaque`), repo `fabreapp`.
Repo PÚBLICO: no commitear credenciales, IPs, datos de clientes ni detalles de seguridad del deploy.

## Estado al 2026-10-06
- MVP desplegado. 19 commits entre 2026-07-11 y 2026-07-12 (mayoría fixes de deploy Coolify y OAuth Google); sin actividad posterior.
- Último commit en `main`: `97501d1` 2026-07-12 "Add clear Google connection status witness on integrations page".
- Ramas vivas: solo `main`. Nada sin mergear.
- Hay un pendiente CRÍTICO de seguridad abierto (ver Pendientes, primer ítem).

## Repo y ramas
- `msantirso-dev/fabreapp` (público).
- Desarrollo y deploy: `main` (según README; sin verificar en Coolify).
- Ramas a borrar: ninguna.

## Stack
- Python 3.12-slim, Django ≥5.0,<6 + DRF, django-environ, django-cors-headers, psycopg 3, gunicorn, whitenoise.
- google-api-python-client / google-auth-oauthlib, afip.py, requests.
- PostgreSQL 16 (prod), SQLite (local).

## Estructura
- `apps/accounts`, `apps/clients` (clientes, CUIT lookup, StudioSettings), `apps/deadlines` (vencimientos, API REST), `apps/calendar_sync` (Google Calendar).
- `config/` (settings, urls, wsgi), `templates/`, `static/`.
- `scripts/entrypoint.sh` (migrate, collectstatic, bootstrap de superusuario, gunicorn), `scripts/healthcheck.sh`.
- `deploy/coolify.env.example`, `deploy/coolify-cron.txt`, `deploy/claude-coolify-fix-502.md` (obsoleto).

## Comandos
- `pip install -r requirements.txt`
- `python manage.py migrate` · `python manage.py createsuperuser` · `python manage.py runserver`
- Tests: `python manage.py test`
- Migraciones: `python manage.py makemigrations <app>` y commitear; en prod las aplica el entrypoint (`migrate --noinput`).
- Cron: `python manage.py sync_google_calendar` (primera vez `--ensure-calendar`).

## Deploy (Coolify)
- Instancia: https://coolify.pit.com.ar
- Recurso: Docker Compose, `docker-compose.yml` raíz [sin verificar].
- Rama: `main` [sin verificar]. UUID: [?] a confirmar.
- Dominio: `app.fabregad.com.ar` (en servicio `web`; siempre incluido en ALLOWED_HOSTS por `config/settings.py`).
- Puerto interno: **8002** (fijo en `Dockerfile:8-9`, `docker-compose.yml:28-31`, `scripts/entrypoint.sh`). Coolify "Ports Exposes" = 8002. README (8000) y `deploy/claude-coolify-fix-502.md` (3000) están desactualizados.
- Health check: `scripts/healthcheck.sh` → `curl http://127.0.0.1:8002/accounts/login/`.
- Servicios: `db` (postgres:16-alpine, volumen `fabreapp_pgdata`), `web` (gunicorn).
- Cron Coolify: `python manage.py sync_google_calendar` cada 10 min (sugerido en `deploy/coolify-cron.txt`) [sin verificar si está creado].
- `COOLIFY_BUILD_ID` (build arg para forzar rebuild) está en `Dockerfile:3` y `docker-compose.yml:22` con valores distintos.
- Backups: [?] no documentados.

## Variables de entorno
Solo nombres. Infra en Coolify; credenciales de Google OAuth y APIs CUIT también desde la UI de integraciones (se guardan en DB).
- App: `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `APP_BASE_URL`, `APPLICATION_NAME`, `PORT`, `APP_PORT`, `COOLIFY_BUILD_ID`
- DB: `DATABASE_URL`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- Google: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, `GOOGLE_CALENDAR_ENABLED`, `GOOGLE_SERVICE_ACCOUNT_FILE`, `GOOGLE_DELEGATED_USER`, `GOOGLE_SHARED_CALENDAR_ID`, `GOOGLE_SHARED_CALENDAR_NAME`, `GOOGLE_CALENDAR_TIMEZONE`, `GOOGLE_CALENDAR_SCHEMA_VERSION`, `GOOGLE_CALENDAR_WEBHOOK_URL`, `GOOGLE_CALENDAR_CHANNEL_TOKEN`
- CUIT: `AFIP_SDK_ACCESS_TOKEN`, `AFIP_SDK_CUIT`, `CUITALIZER_API_KEY`, `CUIT_LOOKUP_URL_TEMPLATE`, `CUIT_LOOKUP_API_KEY`
- Bootstrap de superusuario: `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`, `DJANGO_SUPERUSER_EMAIL` (solo en Coolify; ver Pendientes)

## Integraciones y dependencias compartidas
- Google Calendar: OAuth web configurable desde la UI; sync al calendario compartido inmediato + cron. Si Google falla, la finalización no se revierte.
- AFIP SDK / Cuitalizer / API CUIT genérica para autocompletar razón social (`apps/clients/cuit_lookup.py`).
- Sin código compartido con otros repos de PIT.

## Cómo trabajar y hacer push
- Escritura desde un chat/Proyecto de Claude: llamar a `add_repo` con owner `msantirso-dev`, repo `fabreapp`, `access: "push"`, y clonar donde indique. No pedir PAT ni pegar tokens en el chat.
- Estándar de Max: arquitectura modular (una app Django por dominio), commits atómicos en español `feat(modulo)` / `fix(modulo)`, nunca commitear `.env` ni credenciales, health check vivo (hoy `/accounts/login/`; [REC] sumar `/api/health`), variables en `.env.example` y `deploy/coolify.env.example` solo con placeholders, resumen final ≤5 líneas.
- Push a `main` = deploy automático en Coolify [sin verificar]. Cambios riesgosos (modelos, entrypoint, Dockerfile, OAuth) por rama + PR.
- Antes de declarar algo publicado: verificar en Coolify el commit desplegado.
- Reglas del repo:
  - Repo público: revisar el diff antes de cada push. Nunca valores reales en Dockerfile, compose ni archivos example.
  - Cambios de modelos → `makemigrations` + commit de la migración; no editar migraciones aplicadas.
  - Puerto 8002 fijo: no cambiarlo sin cambiar Coolify en el mismo paso.

## Pendientes y problemas conocidos
Seguridad (CRÍTICO, primero)
- [ ] Contraseña real del superusuario commiteada en `Dockerfile:11`, `docker-compose.yml:47` y `deploy/coolify.env.example:32`, y reaplicada por `scripts/entrypoint.sh` (bloque 28-52) en cada arranque. Acciones, en este orden:
  1. Max rota la contraseña en producción y la carga solo en Coolify (fuera del chat).
  2. Quitar el valor de los tres archivos (Dockerfile sin `ENV` de contraseña; compose sin default; example con placeholder).
  3. Cambiar el entrypoint para que solo cree el superusuario si no existe (sin resetear la contraseña en cada arranque).
  4. Considerar el valor comprometido (queda en el historial git público).
- [ ] Tokens de Google OAuth y API keys CUIT se guardan en DB en texto plano (`apps/clients/models.py`, `apps/calendar_sync/models.py`): evaluar cifrado.
- [ ] Defaults inseguros: `POSTGRES_PASSWORD` en `docker-compose.yml:8,38`; `SECRET_KEY` por defecto en `config/settings.py:16`. Exigir valores de Coolify.
- [ ] Identificadores reales en archivos públicos: `GOOGLE_OAUTH_CLIENT_ID` en `deploy/coolify.env.example:17`; CUIT en `docker-compose.yml:45`, `deploy/coolify.env.example:28`, `.env.example:32`. Reemplazar por placeholders.

Deploy
- [ ] Confirmar en Coolify recurso, rama, puerto 8002, cron y UUID.
- [ ] Unificar `COOLIFY_BUILD_ID` (`Dockerfile:3` vs `docker-compose.yml:22`).
- [ ] Documentar backups de `fabreapp_pgdata`.

Orden / doc
- [ ] README: puerto 8002 (hoy dice 8000), quitar "usar el .env ya incluido" y el paso de `createsuperuser` contradictorio.
- [ ] Borrar o archivar `deploy/claude-coolify-fix-502.md` (obsoleto, dice 3000).
- [ ] Sync bidireccional con Google Calendar (futuro, README).

## Próximo paso
- Documentado: "tras el primer deploy sano, createsuperuser" (README), ya superado por el bootstrap automático.
- [REC] Resolver YA el pendiente crítico del superusuario (rotar, sacar del repo, entrypoint solo crea). Después, alinear README y puerto.
