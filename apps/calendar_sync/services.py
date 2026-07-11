from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.deadlines.models import Deadline, GoogleSyncStatus

from .event_builder import build_google_event_body
from .models import GoogleCalendarConnection
from .oauth import build_calendar_service_from_oauth

logger = logging.getLogger(__name__)


class GoogleCalendarError(Exception):
    pass


class GoogleCalendarNotConfigured(GoogleCalendarError):
    pass


def calendar_sync_ready() -> bool:
    if GoogleCalendarConnection.get_active():
        return True
    return bool(
        settings.GOOGLE_CALENDAR_ENABLED and settings.GOOGLE_SERVICE_ACCOUNT_FILE
    )


@lru_cache(maxsize=1)
def _build_service_account():
    credentials_file = settings.GOOGLE_SERVICE_ACCOUNT_FILE
    if not credentials_file:
        raise GoogleCalendarNotConfigured("GOOGLE_SERVICE_ACCOUNT_FILE is empty")

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/calendar"]
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=scopes,
    )
    if settings.GOOGLE_DELEGATED_USER:
        credentials = credentials.with_subject(settings.GOOGLE_DELEGATED_USER)

    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def get_calendar_service():
    service, connection = build_calendar_service_from_oauth()
    if service is not None:
        return service

    if not settings.GOOGLE_CALENDAR_ENABLED:
        raise GoogleCalendarNotConfigured(
            "Conectá una cuenta Google en Integraciones o configurá service account."
        )
    return _build_service_account()


def clear_calendar_service_cache() -> None:
    _build_service_account.cache_clear()


def ensure_shared_calendar() -> str:
    """
    Devuelve el ID del calendario compartido «Vencimientos – Estudio Contable».
    Lo crea si no existe.
    """
    connection = GoogleCalendarConnection.get_active()
    if connection and connection.shared_calendar_id:
        return connection.shared_calendar_id
    if settings.GOOGLE_SHARED_CALENDAR_ID:
        return settings.GOOGLE_SHARED_CALENDAR_ID

    service = get_calendar_service()
    name = (
        connection.shared_calendar_name
        if connection
        else settings.GOOGLE_SHARED_CALENDAR_NAME
    )

    page_token = None
    while True:
        result = (
            service.calendarList()
            .list(pageToken=page_token, maxResults=250)
            .execute()
        )
        for item in result.get("items", []):
            if item.get("summary") == name:
                calendar_id = item["id"]
                if connection:
                    connection.shared_calendar_id = calendar_id
                    connection.save(update_fields=["shared_calendar_id", "updated_at"])
                return calendar_id
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    created = (
        service.calendars()
        .insert(
            body={
                "summary": name,
                "timeZone": settings.GOOGLE_CALENDAR_TIMEZONE,
                "description": (
                    "Calendario compartido de vencimientos del estudio. "
                    "No editar eventos manualmente para finalizar tareas; "
                    "usar el enlace de la aplicación."
                ),
            }
        )
        .execute()
    )
    calendar_id = created["id"]
    if connection:
        connection.shared_calendar_id = calendar_id
        connection.last_error = ""
        connection.save(
            update_fields=["shared_calendar_id", "last_error", "updated_at"]
        )
    logger.info("Created shared Google Calendar %s (%s)", name, calendar_id)
    return calendar_id


def share_calendar_with_email(calendar_id: str, email: str, role: str = "writer") -> None:
    """Comparte el calendario con una cuenta Google del estudio."""
    service = get_calendar_service()
    service.acl().insert(
        calendarId=calendar_id,
        body={
            "role": role,
            "scope": {"type": "user", "value": email},
        },
        sendNotifications=True,
    ).execute()


def create_or_update_event(deadline: Deadline) -> dict[str, Any]:
    """
    Crea o actualiza el evento en el calendario compartido.
    Nunca crea un evento nuevo si ya existe google_calendar_event_id.
    """
    service = get_calendar_service()
    calendar_id = deadline.google_calendar_id or ensure_shared_calendar()
    body = build_google_event_body(deadline)

    if deadline.google_calendar_event_id:
        event = (
            service.events()
            .patch(
                calendarId=calendar_id,
                eventId=deadline.google_calendar_event_id,
                body=body,
            )
            .execute()
        )
    else:
        event = (
            service.events()
            .insert(calendarId=calendar_id, body=body)
            .execute()
        )

    return {"calendar_id": calendar_id, "event": event}


def sync_deadline_to_google(deadline: Deadline) -> Deadline:
    """Sincroniza un vencimiento al calendario compartido y actualiza campos locales."""
    if not calendar_sync_ready():
        deadline.google_sync_status = GoogleSyncStatus.PENDING
        deadline.google_sync_error = (
            "Google Calendar no conectado. Andá a Integraciones → Google."
        )
        deadline.save(
            update_fields=[
                "google_sync_status",
                "google_sync_error",
                "updated_at",
            ]
        )
        return deadline

    try:
        result = create_or_update_event(deadline)
        event = result["event"]
        deadline.google_calendar_id = result["calendar_id"]
        deadline.google_calendar_event_id = event["id"]
        deadline.google_etag = event.get("etag", "")
        deadline.google_sync_status = GoogleSyncStatus.SYNCED
        deadline.google_sync_error = ""
        deadline.google_last_synced_at = timezone.now()
        if event.get("updated"):
            from dateutil import parser as date_parser

            deadline.google_updated_at = date_parser.isoparse(event["updated"])
        deadline.save(
            update_fields=[
                "google_calendar_id",
                "google_calendar_event_id",
                "google_etag",
                "google_sync_status",
                "google_sync_error",
                "google_last_synced_at",
                "google_updated_at",
                "updated_at",
            ]
        )
        logger.info(
            "Synced deadline %s -> event %s",
            deadline.id,
            deadline.google_calendar_event_id,
        )
    except GoogleCalendarNotConfigured as exc:
        deadline.google_sync_status = GoogleSyncStatus.PENDING
        deadline.google_sync_error = str(exc)
        deadline.save(
            update_fields=["google_sync_status", "google_sync_error", "updated_at"]
        )
        logger.warning("Google Calendar not configured: %s", exc)
    except Exception as exc:  # noqa: BLE001
        deadline.google_sync_status = GoogleSyncStatus.ERROR
        deadline.google_sync_error = str(exc)
        deadline.save(
            update_fields=["google_sync_status", "google_sync_error", "updated_at"]
        )
        connection = GoogleCalendarConnection.get_active()
        if connection:
            connection.last_error = str(exc)
            connection.save(update_fields=["last_error", "updated_at"])
        logger.exception("Failed to sync deadline %s", deadline.id)
        raise

    return deadline


def try_sync_deadline(deadline: Deadline) -> Deadline:
    """Best-effort sync: never raises; leaves PENDING/ERROR for retry."""
    try:
        return sync_deadline_to_google(deadline)
    except Exception:  # noqa: BLE001
        deadline.refresh_from_db()
        return deadline


def sync_pending_deadlines(limit: int = 100) -> dict[str, int]:
    qs = (
        Deadline.objects.filter(
            google_sync_status__in=[GoogleSyncStatus.PENDING, GoogleSyncStatus.ERROR]
        )
        .select_related("client", "assigned_to", "completed_by")
        .order_by("updated_at")[:limit]
    )
    stats = {"synced": 0, "errors": 0, "skipped": 0}
    for deadline in qs:
        try:
            sync_deadline_to_google(deadline)
            if deadline.google_sync_status == GoogleSyncStatus.SYNCED:
                stats["synced"] += 1
            else:
                stats["skipped"] += 1
        except Exception:  # noqa: BLE001
            stats["errors"] += 1
    return stats
