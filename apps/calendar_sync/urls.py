from django.urls import path

from apps.calendar_sync.views import (
    GoogleIntegrationView,
    google_connect_callback,
    google_connect_start,
    google_disconnect,
    google_sync_now,
)

urlpatterns = [
    path("integraciones/google/", GoogleIntegrationView.as_view(), name="google-integration"),
    path("integraciones/google/conectar/", google_connect_start, name="google-connect"),
    path(
        "integraciones/google/callback/",
        google_connect_callback,
        name="google-callback",
    ),
    path(
        "integraciones/google/desconectar/",
        google_disconnect,
        name="google-disconnect",
    ),
    path(
        "integraciones/google/sincronizar/",
        google_sync_now,
        name="google-sync-now",
    ),
]
