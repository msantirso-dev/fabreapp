# Fabrenaque — Vencimientos & calendario compartido

Sistema contable (MVP) con **calendario de Google compartido** y finalización colaborativa de vencimientos.

## Idea central

- Un solo calendario: **Vencimientos – Estudio Contable**
- Los eventos viven ahí; se comparte con las cuentas Google del estudio
- **No** se crean copias en calendarios personales
- Al completar una tarea se **actualiza el mismo evento** (`google_calendar_event_id`)

## Stack

- Django 5 + Django REST Framework
- PostgreSQL (producción) / SQLite (local)
- Google Calendar API (service account + domain-wide delegation opcional)

## Arranque local

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # o usar el .env ya incluido
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Web: http://localhost:8000/deadlines/
- Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/v1/deadlines/

## Modelo de vencimiento

| Campo | Uso |
|-------|-----|
| `assigned_to` | Responsable |
| `created_by` | Quién lo creó |
| `completed_by` / `completed_at` | Quién/cuándo lo cerró |
| `status` | PENDING, IN_PROGRESS, WAITING_INFORMATION, READY, COMPLETED, OVERDUE, NOT_APPLICABLE, CANCELLED |
| `observations` | Texto libre |
| `google_calendar_event_id` | Evento en el calendario compartido |
| `google_sync_status` | PENDING / SYNCED / ERROR |

Campos preparados para sync bidireccional futuro (no usados en MVP): `google_etag`, `google_updated_at`, settings `GOOGLE_CALENDAR_WEBHOOK_URL` / `GOOGLE_CALENDAR_CHANNEL_TOKEN`.

## Finalización segura

El enlace del calendario apunta a:

`/deadlines/{id}/complete`

- **GET** → pide login + muestra confirmación (nunca completa)
- **POST** → CSRF + permisos + observación opcional + auditoría

API:

```http
POST /api/v1/deadlines/{id}/complete/
Content-Type: application/json

{ "observation": "Presentación realizada correctamente" }
```

Respuesta:

```json
{
  "id": "UUID",
  "status": "COMPLETED",
  "completed_by": { "id": "UUID", "name": "María López" },
  "completed_at": "2026-08-19T16:42:00-03:00",
  "google_sync_status": "SYNCED"
}
```

Idempotente: completar dos veces no duplica efectos. Si Google falla, la finalización **no se revierte** (`google_sync_status=ERROR`).

## Deploy en Coolify / producción

Dominio: **https://app.fabregad.com.ar**

### Recomendado: Docker Compose

1. En Coolify creá un recurso **Docker Compose** apuntando al repo `msantirso-dev/fabreapp`.
2. Usá el archivo `docker-compose.yml` de la raíz.
3. Definí al menos estas variables en Coolify:
   - `SECRET_KEY` (obligatoria)
   - `POSTGRES_PASSWORD` (cambiá el default)
   - `DATABASE_URL=postgres://fabreapp:TU_PASSWORD@db:5432/fabreapp`
   - `ALLOWED_HOSTS=app.fabregad.com.ar`
   - `CSRF_TRUSTED_ORIGINS=https://app.fabregad.com.ar`
   - `APP_BASE_URL=https://app.fabregad.com.ar`
   - `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`
   - `GOOGLE_OAUTH_REDIRECT_URI=https://app.fabregad.com.ar/integraciones/google/callback/`
4. Puerto del servicio web: **8000**
5. En Google Cloud agregá la URI de callback de producción.
6. Tras el primer deploy sano:
   ```bash
   python manage.py createsuperuser
   ```
7. Cron cada 10–60 min: `python manage.py sync_google_calendar`

Si ves **Bad Gateway**: el contenedor `web` no está listo. Mirá logs de `web` (migrate/DB/SECRET_KEY) y que Coolify apunte al puerto 8000.

## Google Calendar (OAuth desde la UI)

1. En [Google Cloud Console](https://console.cloud.google.com/): creá un proyecto, habilitá **Google Calendar API**, creá credenciales **OAuth 2.0** (app web).
2. URI de redirección: `http://127.0.0.1:8000/integraciones/google/callback/`
3. Completá en `.env`:

```env
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/integraciones/google/callback/
APP_BASE_URL=http://127.0.0.1:8000
```

4. Entrá como staff a **Google** en el menú → **Conectar cuenta Google**.
5. Se crea el calendario compartido `Vencimientos – Estudio Contable`.

## Autocompletar CUIT

Al crear un cliente, al escribir el CUIT se consulta un proveedor y se completa la razón social.

Configurá en `.env` **al menos uno**:

```env
CUITALIZER_API_KEY=ctlz_...
# o
CUIT_LOOKUP_URL_TEMPLATE=https://tu-api.example/cuit/{cuit}
CUIT_LOOKUP_API_KEY=
```

Sin API key, el formulario sigue funcionando: cargás la razón social a mano.

### Títulos de evento

| Estado | Título |
|--------|--------|
| Pendiente | 🔵 IVA – EMPRESA… |
| En proceso / listo / esperando | 🟡 … |
| Completado | ✅ … |
| Vencido | 🔴 … |

Identificación estable vía `extendedProperties.private` (`deadline_id`, `client_id`, `obligation_code`, `period`, `assigned_user_id`, `application_name`, `schema_version`).

En MVP, ediciones manuales en Google **no** se interpretan como finalización.

## Coolify — sync programado

Comando:

```bash
python manage.py sync_google_calendar
```

Frecuencia recomendada: **cada 10 minutos** (o cada hora en la primera versión).

Además hay sync inmediato al crear, cambiar fecha, asignar, completar o cancelar. Si falla, queda `PENDING`/`ERROR` para el cron.

## Auditoría

Cada finalización registra: usuario, fecha/hora, estado anterior/nuevo, observación, IP, `google_calendar_event_id`, resultado de sync. Visible en el detalle del vencimiento y en `/api/v1/deadlines/{id}/audit/`.

## Tests

```bash
python manage.py test
```
