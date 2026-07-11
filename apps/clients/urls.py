from django.urls import path

from apps.clients.views import CuitIntegrationView, lookup_cuit_api

urlpatterns = [
    path("api/v1/clients/lookup-cuit/", lookup_cuit_api, name="client-lookup-cuit"),
    path("integraciones/cuit/", CuitIntegrationView.as_view(), name="cuit-integration"),
]
