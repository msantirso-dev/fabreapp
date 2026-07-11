import uuid

from django.conf import settings
from django.db import models


class GoogleCalendarConnection(models.Model):
    """
    Conexión OAuth del estudio a Google Calendar.
    Un único calendario compartido; no se copian eventos a calendarios personales.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="google_calendar_connections",
    )
    google_email = models.EmailField(blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    scopes = models.TextField(blank=True)
    shared_calendar_id = models.CharField(max_length=255, blank=True)
    shared_calendar_name = models.CharField(
        max_length=255,
        default="Vencimientos – Estudio Contable",
    )
    is_active = models.BooleanField(default=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conexión Google Calendar"
        verbose_name_plural = "Conexiones Google Calendar"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        status = "activa" if self.is_active and self.refresh_token else "inactiva"
        return f"{self.google_email or 'Sin email'} ({status})"

    @classmethod
    def get_active(cls):
        return (
            cls.objects.filter(is_active=True)
            .exclude(refresh_token="")
            .order_by("-updated_at")
            .first()
        )
