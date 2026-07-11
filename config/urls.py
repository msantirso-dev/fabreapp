from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.deadlines.api_urls")),
    path("", include("apps.clients.urls")),
    path("", include("apps.calendar_sync.urls")),
    path("", include("apps.deadlines.urls")),
]
