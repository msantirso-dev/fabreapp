from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.decorators.http import require_GET

from apps.clients.cuit_lookup import (
    CuitLookupError,
    format_cuit,
    has_cuit_provider,
    lookup_cuit,
    normalize_cuit,
)
from apps.clients.forms import StudioSettingsForm
from apps.clients.models import StudioSettings


@login_required
@require_GET
def lookup_cuit_api(request):
    raw = request.GET.get("cuit", "")
    try:
        data = lookup_cuit(raw)
        return JsonResponse(
            {
                "ok": True,
                "cuit": data["cuit"],
                "name": data["name"],
                "provider": data.get("provider", ""),
            }
        )
    except CuitLookupError as exc:
        status = 400
        if exc.code == "needs_config":
            status = 503
        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
                "code": exc.code,
                "cuit": format_cuit(normalize_cuit(raw)),
                "configure_url": "/integraciones/cuit/",
            },
            status=status,
        )


class CuitIntegrationView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "integrations/cuit.html"

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        settings_obj = StudioSettings.load()
        form = StudioSettingsForm(instance=settings_obj)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "has_provider": has_cuit_provider(),
            },
        )

    def post(self, request):
        settings_obj = StudioSettings.load()
        form = StudioSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración de consulta CUIT guardada.")
            return redirect("cuit-integration")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "has_provider": has_cuit_provider(),
            },
            status=400,
        )
