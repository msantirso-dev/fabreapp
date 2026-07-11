import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class DeadlineStatus(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    IN_PROGRESS = "IN_PROGRESS", "En proceso"
    WAITING_INFORMATION = "WAITING_INFORMATION", "Esperando información"
    READY = "READY", "Listo"
    COMPLETED = "COMPLETED", "Completado"
    OVERDUE = "OVERDUE", "Vencido"
    NOT_APPLICABLE = "NOT_APPLICABLE", "No aplica"
    CANCELLED = "CANCELLED", "Cancelado"


class GoogleSyncStatus(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    SYNCED = "SYNCED", "Sincronizado"
    ERROR = "ERROR", "Error"


class Deadline(models.Model):
    """Vencimiento contable vinculado a un único evento del calendario compartido."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="deadlines",
    )
    obligation_code = models.CharField("Código de obligación", max_length=64)
    obligation_name = models.CharField("Obligación", max_length=255)
    period = models.CharField(
        "Período fiscal",
        max_length=7,
        help_text="Formato MM/YYYY, p.ej. 07/2026",
    )
    due_date = models.DateField("Fecha de vencimiento")

    status = models.CharField(
        max_length=32,
        choices=DeadlineStatus.choices,
        default=DeadlineStatus.PENDING,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_deadlines",
        verbose_name="Responsable",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_deadlines",
        verbose_name="Creado por",
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_deadlines",
        verbose_name="Completado por",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    observations = models.TextField(blank=True)

    google_calendar_event_id = models.CharField(max_length=255, blank=True, db_index=True)
    google_calendar_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID del calendario compartido donde vive el evento.",
    )
    google_sync_status = models.CharField(
        max_length=16,
        choices=GoogleSyncStatus.choices,
        default=GoogleSyncStatus.PENDING,
        db_index=True,
    )
    google_sync_error = models.TextField(blank=True)
    google_last_synced_at = models.DateTimeField(null=True, blank=True)

    # Prepared for future bidirectional sync via Google push notifications (MVP: unused)
    google_etag = models.CharField(max_length=255, blank=True)
    google_updated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "obligation_code"]
        verbose_name = "Vencimiento"
        verbose_name_plural = "Vencimientos"
        indexes = [
            models.Index(fields=["google_sync_status", "updated_at"]),
            models.Index(fields=["status", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.obligation_name} – {self.client.name} ({self.due_date})"

    @property
    def is_completed(self) -> bool:
        return self.status == DeadlineStatus.COMPLETED

    def mark_sync_pending(self, *, save: bool = True) -> None:
        self.google_sync_status = GoogleSyncStatus.PENDING
        self.google_sync_error = ""
        if save:
            self.save(
                update_fields=[
                    "google_sync_status",
                    "google_sync_error",
                    "updated_at",
                ]
            )

    def refresh_overdue_status(self) -> bool:
        """Promote PENDING-like items past due_date to OVERDUE. Returns True if changed."""
        if self.status in {
            DeadlineStatus.COMPLETED,
            DeadlineStatus.CANCELLED,
            DeadlineStatus.NOT_APPLICABLE,
            DeadlineStatus.OVERDUE,
        }:
            return False
        if self.due_date < timezone.localdate():
            self.status = DeadlineStatus.OVERDUE
            return True
        return False


class DeadlineAuditLog(models.Model):
    """Historial de cambios de un vencimiento (visible en el detalle)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deadline = models.ForeignKey(
        Deadline,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deadline_audit_logs",
    )
    action = models.CharField(max_length=64)
    previous_status = models.CharField(max_length=32, blank=True)
    new_status = models.CharField(max_length=32, blank=True)
    observation = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    google_calendar_event_id = models.CharField(max_length=255, blank=True)
    google_sync_result = models.CharField(max_length=32, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Auditoría de vencimiento"
        verbose_name_plural = "Auditorías de vencimientos"

    def __str__(self) -> str:
        return f"{self.action} @ {self.created_at:%Y-%m-%d %H:%M}"
