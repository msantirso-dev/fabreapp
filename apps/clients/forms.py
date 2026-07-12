from django import forms

from apps.clients.models import StudioSettings


class StudioSettingsForm(forms.ModelForm):
    class Meta:
        model = StudioSettings
        fields = (
            "afip_sdk_access_token",
            "afip_sdk_cuit",
            "afip_sdk_production",
            "cuitalizer_api_key",
            "cuit_lookup_url_template",
            "cuit_lookup_api_key",
        )
        labels = {
            "afip_sdk_access_token": "Afip SDK access token",
            "afip_sdk_cuit": "CUIT Afip SDK",
            "afip_sdk_production": "Usar producción ARCA",
            "cuitalizer_api_key": "Cuitalizer API key",
            "cuit_lookup_url_template": "URL template alternativa",
            "cuit_lookup_api_key": "API key alternativa",
        }
        widgets = {
            "afip_sdk_access_token": forms.PasswordInput(
                render_value=True,
                attrs={"placeholder": "Token de https://app.afipsdk.com", "autocomplete": "off"},
            ),
            "cuitalizer_api_key": forms.PasswordInput(
                render_value=True,
                attrs={"placeholder": "ctlz_...", "autocomplete": "off"},
            ),
            "cuit_lookup_url_template": forms.TextInput(
                attrs={"placeholder": "https://tu-api.example/cuit/{cuit}"}
            ),
        }
        help_texts = {
            "afip_sdk_access_token": "Creá una cuenta gratis en app.afipsdk.com y pegá el token.",
            "afip_sdk_cuit": "En desarrollo usá 20-40937847-2. En producción, el CUIT de tu certificado.",
            "afip_sdk_production": "Solo con certificado propio cargado en Afip SDK.",
        }


class GoogleOAuthSettingsForm(forms.ModelForm):
    class Meta:
        model = StudioSettings
        fields = (
            "google_oauth_client_id",
            "google_oauth_client_secret",
            "google_oauth_redirect_uri",
            "app_base_url",
        )
        labels = {
            "google_oauth_client_id": "Google OAuth Client ID",
            "google_oauth_client_secret": "Google OAuth Client Secret",
            "google_oauth_redirect_uri": "URI de redirección",
            "app_base_url": "URL base de la aplicación",
        }
        widgets = {
            # TextInput (no password): evita que el browser omita el valor al guardar
            "google_oauth_client_id": forms.TextInput(
                attrs={
                    "placeholder": "xxxxx.apps.googleusercontent.com",
                    "autocomplete": "off",
                    "spellcheck": "false",
                }
            ),
            "google_oauth_client_secret": forms.TextInput(
                attrs={
                    "placeholder": "GOCSPX-...",
                    "autocomplete": "off",
                    "spellcheck": "false",
                }
            ),
            "google_oauth_redirect_uri": forms.TextInput(
                attrs={
                    "placeholder": "https://app.fabregad.com.ar/integraciones/google/callback/",
                    "spellcheck": "false",
                }
            ),
            "app_base_url": forms.TextInput(
                attrs={
                    "placeholder": "https://app.fabregad.com.ar",
                    "spellcheck": "false",
                }
            ),
        }
        help_texts = {
            "google_oauth_client_id": "Desde Google Cloud → Credenciales OAuth 2.0.",
            "google_oauth_client_secret": "El secret de la misma credencial OAuth.",
            "google_oauth_redirect_uri": "Debe coincidir exacto con la URI autorizada en Google Cloud.",
            "app_base_url": "URL pública HTTPS de la app (sin barra final).",
        }

    def clean_google_oauth_client_id(self):
        return (self.cleaned_data.get("google_oauth_client_id") or "").strip()

    def clean_google_oauth_client_secret(self):
        return (self.cleaned_data.get("google_oauth_client_secret") or "").strip()

    def clean_google_oauth_redirect_uri(self):
        value = (self.cleaned_data.get("google_oauth_redirect_uri") or "").strip()
        if value and not value.startswith(("http://", "https://")):
            raise forms.ValidationError("La URI debe empezar con https://")
        return value

    def clean_app_base_url(self):
        value = (self.cleaned_data.get("app_base_url") or "").strip().rstrip("/")
        if value and not value.startswith(("http://", "https://")):
            raise forms.ValidationError("La URL debe empezar con https://")
        return value
