from django.utils import timezone

from .models import Deadline, DeadlineAuditLog, DeadlineStatus, GoogleSyncStatus


def get_client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def write_audit(
    *,
    deadline: Deadline,
    actor,
    action: str,
    previous_status: str = "",
    new_status: str = "",
    observation: str = "",
    ip_address: str | None = None,
    google_calendar_event_id: str = "",
    google_sync_result: str = "",
    metadata: dict | None = None,
) -> DeadlineAuditLog:
    return DeadlineAuditLog.objects.create(
        deadline=deadline,
        actor=actor,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        observation=observation,
        ip_address=ip_address,
        google_calendar_event_id=google_calendar_event_id
        or deadline.google_calendar_event_id,
        google_sync_result=google_sync_result,
        metadata=metadata or {},
    )


def complete_deadline(
    *,
    deadline: Deadline,
    user,
    observation: str = "",
    request=None,
    sync_immediately: bool = True,
) -> Deadline:
    """
    Marca un vencimiento como COMPLETED de forma idempotente.

    - No revierte la finalización si falla Google Calendar.
    - Conserva google_calendar_event_id (actualiza el mismo evento).
    """
    if deadline.status == DeadlineStatus.COMPLETED:
        return deadline

    if deadline.status in {DeadlineStatus.CANCELLED, DeadlineStatus.NOT_APPLICABLE}:
        raise ValueError(
            f"No se puede completar un vencimiento en estado {deadline.status}."
        )

    previous_status = deadline.status
    now = timezone.now()
    deadline.status = DeadlineStatus.COMPLETED
    deadline.completed_by = user
    deadline.completed_at = now
    if observation:
        deadline.observations = observation
    deadline.google_sync_status = GoogleSyncStatus.PENDING
    deadline.google_sync_error = ""
    deadline.save()

    sync_result = ""
    if sync_immediately:
        from apps.calendar_sync.services import sync_deadline_to_google

        try:
            sync_deadline_to_google(deadline)
            deadline.refresh_from_db()
            sync_result = deadline.google_sync_status
        except Exception as exc:  # noqa: BLE001 — persist completion anyway
            deadline.google_sync_status = GoogleSyncStatus.ERROR
            deadline.google_sync_error = str(exc)
            deadline.save(
                update_fields=[
                    "google_sync_status",
                    "google_sync_error",
                    "updated_at",
                ]
            )
            sync_result = GoogleSyncStatus.ERROR

    write_audit(
        deadline=deadline,
        actor=user,
        action="COMPLETE",
        previous_status=previous_status,
        new_status=DeadlineStatus.COMPLETED,
        observation=observation,
        ip_address=get_client_ip(request),
        google_calendar_event_id=deadline.google_calendar_event_id,
        google_sync_result=sync_result,
    )
    return deadline
