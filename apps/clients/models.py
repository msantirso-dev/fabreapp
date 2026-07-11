from django.db import models


class Client(models.Model):
    """Cliente / empresa del estudio contable."""

    name = models.CharField("Razón social", max_length=255)
    cuit = models.CharField("CUIT", max_length=13, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self) -> str:
        return f"{self.name} ({self.cuit})"


class StudioSettings(models.Model):
    """Configuración del estudio (singleton lógico, id=1)."""

    cuitalizer_api_key = models.CharField(max_length=255, blank=True)
    cuit_lookup_url_template = models.CharField(
        max_length=500,
        blank=True,
        help_text="Ej: https://tu-api.example/cuit/{cuit}",
    )
    cuit_lookup_api_key = models.CharField(max_length=255, blank=True)
    afip_sdk_access_token = models.CharField(max_length=255, blank=True)
    afip_sdk_cuit = models.CharField(
        max_length=13,
        blank=True,
        default="20-40937847-2",
        help_text="CUIT del certificado / entorno Afip SDK. En desarrollo: 20-40937847-2",
    )
    afip_sdk_production = models.BooleanField(
        default=False,
        help_text="Usar producción ARCA (requiere certificado propio en Afip SDK).",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración del estudio"
        verbose_name_plural = "Configuración del estudio"

    def __str__(self) -> str:
        return "Configuración del estudio"

    @classmethod
    def load(cls) -> "StudioSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
