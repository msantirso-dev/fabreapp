from __future__ import annotations

from datetime import date, datetime

from django.conf import settings
from django.utils import timezone

from apps.deadlines.models import Deadline, DeadlineStatus

STATUS_EMOJI = {
    DeadlineStatus.PENDING: "🔵",
    DeadlineStatus.IN_PROGRESS: "🟡",
    DeadlineStatus.WAITING_INFORMATION: "🟡",
    DeadlineStatus.READY: "🟡",
    DeadlineStatus.COMPLETED: "✅",
    DeadlineStatus.OVERDUE: "🔴",
    DeadlineStatus.NOT_APPLICABLE: "⚪",
    DeadlineStatus.CANCELLED: "⚫",
}

# Google Calendar colorId (event colors)
STATUS_COLOR_ID = {
    DeadlineStatus.PENDING: "9",  # blueberry / blue
    DeadlineStatus.IN_PROGRESS: "5",  # banana / yellow
    DeadlineStatus.WAITING_INFORMATION: "5",
    DeadlineStatus.READY: "5",
    DeadlineStatus.COMPLETED: "10",  # basil / green
    DeadlineStatus.OVERDUE: "11",  # tomato / red
    DeadlineStatus.NOT_APPLICABLE: "8",  # graphite
    DeadlineStatus.CANCELLED: "8",
}


def _format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _format_datetime(value: datetime) -> str:
    local = timezone.localtime(value)
    return local.strftime("%d/%m/%Y %H:%M")


def build_event_title(deadline: Deadline) -> str:
    emoji = STATUS_EMOJI.get(deadline.status, "🔵")
    return f"{emoji} {deadline.obligation_name} – {deadline.client.name}"


def build_event_description(deadline: Deadline) -> str:
    base = settings.APP_BASE_URL.rstrip("/")
    detail_url = f"{base}/deadlines/{deadline.id}"
    complete_url = f"{base}/deadlines/{deadline.id}/complete"

    lines = [
        f"Cliente: {deadline.client.name}",
        f"CUIT: {deadline.client.cuit}",
        f"Obligación: {deadline.obligation_name}",
        f"Período fiscal: {deadline.period}",
        f"Fecha de vencimiento: {_format_date(deadline.due_date)}",
    ]

    if deadline.status == DeadlineStatus.COMPLETED:
        completed_by = (
            deadline.completed_by.get_full_name_or_username()
            if deadline.completed_by
            else "—"
        )
        completed_at = (
            _format_datetime(deadline.completed_at) if deadline.completed_at else "—"
        )
        lines.extend(
            [
                "Estado: Completado",
                f"Completado por: {completed_by}",
                f"Fecha de finalización: {completed_at}",
                f"Observación: {deadline.observations or '—'}",
                "",
                "Ver detalle:",
                detail_url,
            ]
        )
    else:
        responsible = (
            deadline.assigned_to.get_full_name_or_username()
            if deadline.assigned_to
            else "Sin asignar"
        )
        status_label = deadline.get_status_display()
        lines.extend(
            [
                f"Responsable: {responsible}",
                f"Estado: {status_label}",
                "",
                "Abrir tarea:",
                detail_url,
                "",
                "Marcar como completado:",
                complete_url,
            ]
        )

    return "\n".join(lines)


def build_extended_properties(deadline: Deadline) -> dict:
    return {
        "private": {
            "deadline_id": str(deadline.id),
            "client_id": str(deadline.client_id),
            "obligation_code": deadline.obligation_code,
            "period": deadline.period,
            "assigned_user_id": str(deadline.assigned_to_id or ""),
            "application_name": settings.APPLICATION_NAME,
            "schema_version": str(settings.GOOGLE_CALENDAR_SCHEMA_VERSION),
        }
    }


def build_google_event_body(deadline: Deadline) -> dict:
    """All-day event payload for the shared calendar."""
    due = deadline.due_date
    # Google all-day end is exclusive
    end = due.toordinal() + 1
    end_date = date.fromordinal(end)

    body = {
        "summary": build_event_title(deadline),
        "description": build_event_description(deadline),
        "start": {"date": due.isoformat()},
        "end": {"date": end_date.isoformat()},
        "colorId": STATUS_COLOR_ID.get(deadline.status, "9"),
        "extendedProperties": build_extended_properties(deadline),
        "transparency": "transparent",
    }
    return body
