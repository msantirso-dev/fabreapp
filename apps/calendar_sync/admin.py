from django.contrib import admin

from .models import GoogleCalendarConnection


@admin.register(GoogleCalendarConnection)
class GoogleCalendarConnectionAdmin(admin.ModelAdmin):
    list_display = (
        "google_email",
        "shared_calendar_id",
        "is_active",
        "connected_by",
        "updated_at",
    )
    readonly_fields = (
        "access_token",
        "refresh_token",
        "token_expiry",
        "scopes",
        "created_at",
        "updated_at",
    )
    search_fields = ("google_email", "shared_calendar_id")
