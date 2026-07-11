from django.contrib import admin

from .models import Deadline, DeadlineAuditLog


class DeadlineAuditLogInline(admin.TabularInline):
    model = DeadlineAuditLog
    extra = 0
    readonly_fields = (
        "actor",
        "action",
        "previous_status",
        "new_status",
        "observation",
        "ip_address",
        "google_calendar_event_id",
        "google_sync_result",
        "created_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = (
        "obligation_name",
        "client",
        "period",
        "due_date",
        "status",
        "assigned_to",
        "google_sync_status",
        "completed_at",
    )
    list_filter = ("status", "google_sync_status", "obligation_code")
    search_fields = (
        "obligation_name",
        "obligation_code",
        "client__name",
        "client__cuit",
        "google_calendar_event_id",
    )
    raw_id_fields = ("client", "assigned_to", "created_by", "completed_by")
    readonly_fields = (
        "completed_by",
        "completed_at",
        "google_calendar_event_id",
        "google_calendar_id",
        "google_last_synced_at",
        "google_etag",
        "google_updated_at",
        "created_at",
        "updated_at",
    )
    inlines = [DeadlineAuditLogInline]


@admin.register(DeadlineAuditLog)
class DeadlineAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "deadline",
        "action",
        "actor",
        "previous_status",
        "new_status",
        "google_sync_result",
        "created_at",
    )
    list_filter = ("action", "new_status")
    search_fields = ("deadline__id", "observation", "google_calendar_event_id")
    readonly_fields = [f.name for f in DeadlineAuditLog._meta.fields]
