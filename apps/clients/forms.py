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
