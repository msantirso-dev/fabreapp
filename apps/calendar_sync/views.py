from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.db import OperationalError, ProgrammingError
from django.shortcuts import redirect, render
from django.views import View

from apps.calendar_sync.models import GoogleCalendarConnection
from apps.calendar_sync.oauth import (
    GoogleOAuthNotConfigured,
    build_oauth_flow,
    fetch_google_email,
    oauth_is_configured,
    save_connection_from_credentials,
)
from apps.calendar_sync.services import (
    clear_calendar_service_cache,
    ensure_shared_calendar,
    sync_pending_deadlines,
)
from apps.clients.forms import GoogleOAuthSettingsForm
from apps.clients.models import StudioSettings


def _is_staff(user) -> bool:
    return bool(user.is_authenticated and user.is_staff)


class GoogleIntegrationView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "integrations/google.html"

    def test_func(self):
        return _is_staff(self.request.user)

    def _context(self, request, form=None):
        studio = StudioSettings.load()
        suggested_redirect = (
            "https://app.fabregad.com.ar/integraciones/google/callback/"
        )
        suggested_base = "https://app.fabregad.com.ar"
        connection = GoogleCalendarConnection.get_active()
        oauth_ok = oauth_is_configured()
        if connection:
            google_status = "connected"
        elif oauth_ok:
            google_status = "credentials_ready"
        else:
            google_status = "not_configured"

        if form is None:
            initial = {
                "google_oauth_client_id": studio.google_oauth_client_id,
                "google_oauth_client_secret": studio.google_oauth_client_secret,
                "google_oauth_redirect_uri": studio.google_oauth_redirect_uri
                or suggested_redirect,
                "app_base_url": studio.app_base_url or suggested_base,
            }
            form = GoogleOAuthSettingsForm(initial=initial, instance=studio)
        return {
            "connection": connection,
            "oauth_configured": oauth_ok,
            "google_status": google_status,
            "redirect_uri": studio.google_oauth_redirect_uri or suggested_redirect,
            "saved_client_id": studio.google_oauth_client_id,
            "has_client_secret": bool(studio.google_oauth_client_secret),
            "form": form,
        }

    def get(self, request):
        return render(request, self.template_name, self._context(request))

    def post(self, request):
        studio = StudioSettings.load()
        form = GoogleOAuthSettingsForm(request.POST, instance=studio)
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.save(
                    update_fields=[
                        "google_oauth_client_id",
                        "google_oauth_client_secret",
                        "google_oauth_redirect_uri",
                        "app_base_url",
                        "updated_at",
                    ]
                )
                messages.success(
                    request,
                    "Credenciales OAuth guardadas. Ya podés conectar la cuenta Google.",
                )
                return redirect("google-integration")
            except (OperationalError, ProgrammingError) as exc:
                messages.error(
                    request,
                    "No se pudo guardar: falta migrar la base. "
                    "Redeployá la app o ejecutá: python manage.py migrate. "
                    f"Detalle: {exc}",
                )
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f"No se pudo guardar: {exc}")
        else:
            messages.error(
                request,
                "No se pudo guardar. Revisá los errores del formulario.",
            )
        return render(
            request,
            self.template_name,
            self._context(request, form=form),
            status=400,
        )


@login_required
@user_passes_test(_is_staff)
def google_connect_start(request):
    try:
        flow = build_oauth_flow()
    except GoogleOAuthNotConfigured as exc:
        messages.error(request, str(exc))
        return redirect("google-integration")

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["google_oauth_state"] = state
    request.session.modified = True
    cache.set(f"google_oauth_state:{request.user.id}", state, timeout=600)
    return redirect(authorization_url)


@login_required
@user_passes_test(_is_staff)
def google_connect_callback(request):
    expected_state = request.session.pop("google_oauth_state", None)
    cached_state = cache.get(f"google_oauth_state:{request.user.id}")
    cache.delete(f"google_oauth_state:{request.user.id}")
    state = request.GET.get("state")
    if not state or state not in {expected_state, cached_state}:
        messages.error(
            request,
            "Estado OAuth inválido o la sesión expiró al volver de Google. "
            "Probá conectar de nuevo (usá el mismo navegador).",
        )
        return redirect("google-integration")

    if request.GET.get("error"):
        messages.error(
            request,
            f"Google rechazó la conexión: {request.GET.get('error_description') or request.GET.get('error')}",
        )
        return redirect("google-integration")

    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google no devolvió el código de autorización.")
        return redirect("google-integration")

    connection = None
    try:
        flow = build_oauth_flow(state=state)
        # Usar code directo: más fiable detrás de proxy HTTPS (Coolify)
        flow.fetch_token(code=code)
        credentials = flow.credentials
        if not credentials.token:
            raise RuntimeError("Google no devolvió access_token.")

        email = ""
        try:
            email = fetch_google_email(credentials)
        except Exception as exc:  # noqa: BLE001
            email = ""
            messages.warning(request, f"Conectado, pero no se pudo leer el email: {exc}")

        connection = save_connection_from_credentials(
            credentials=credentials,
            user=request.user,
            google_email=email,
        )
        clear_calendar_service_cache()

        calendar_id = ""
        try:
            calendar_id = ensure_shared_calendar()
            connection.refresh_from_db()
        except Exception as exc:  # noqa: BLE001
            connection.last_error = str(exc)
            connection.save(update_fields=["last_error", "updated_at"])
            messages.warning(
                request,
                f"Cuenta Google vinculada ({email or 'sin email'}), "
                f"pero falló la creación del calendario: {exc}",
            )
            return redirect("google-integration")

        messages.success(
            request,
            f"Cuenta Google conectada ({email or 'OK'}). "
            f"Calendario compartido: {calendar_id or connection.shared_calendar_id}",
        )
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f"No se pudo completar la conexión: {exc}")
    return redirect("google-integration")


@login_required
@user_passes_test(_is_staff)
def google_disconnect(request):
    if request.method != "POST":
        return redirect("google-integration")
    GoogleCalendarConnection.objects.filter(is_active=True).update(is_active=False)
    clear_calendar_service_cache()
    messages.success(request, "Cuenta Google desconectada.")
    return redirect("google-integration")


@login_required
@user_passes_test(_is_staff)
def google_sync_now(request):
    if request.method != "POST":
        return redirect("google-integration")
    if not GoogleCalendarConnection.get_active():
        messages.error(request, "Primero conectá una cuenta Google.")
        return redirect("google-integration")
    try:
        ensure_shared_calendar()
        stats = sync_pending_deadlines(limit=200)
        messages.success(
            request,
            f"Sincronización: synced={stats['synced']} errors={stats['errors']} skipped={stats['skipped']}",
        )
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f"Error al sincronizar: {exc}")
    return redirect("google-integration")
