from django.contrib import admin

from .models import Client, StudioSettings


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "cuit", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "cuit")


@admin.register(StudioSettings)
class StudioSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "afip_sdk_cuit", "afip_sdk_production", "updated_at")
