from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Deadline, GoogleSyncStatus


_SYNC_FIELDS = {
    "due_date",
    "assigned_to_id",
    "status",
    "obligation_code",
    "obligation_name",
    "period",
    "client_id",
    "observations",
}


@receiver(pre_save, sender=Deadline)
def mark_google_sync_pending_on_change(sender, instance: Deadline, **kwargs):
    """Al cambiar un vencimiento, encolar sincronización con el calendario compartido."""
    if not instance.pk:
        instance.google_sync_status = GoogleSyncStatus.PENDING
        return

    try:
        previous = Deadline.objects.get(pk=instance.pk)
    except Deadline.DoesNotExist:
        instance.google_sync_status = GoogleSyncStatus.PENDING
        return

    changed = any(
        getattr(previous, field) != getattr(instance, field) for field in _SYNC_FIELDS
    )
    if changed and instance.google_sync_status == GoogleSyncStatus.SYNCED:
        instance.google_sync_status = GoogleSyncStatus.PENDING
        instance.google_sync_error = ""
