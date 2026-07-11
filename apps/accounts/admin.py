from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Estudio", {"fields": ("google_email", "display_name")}),
    )
    list_display = ("username", "email", "google_email", "display_name", "is_staff")
    search_fields = ("username", "email", "google_email", "display_name", "first_name", "last_name")
