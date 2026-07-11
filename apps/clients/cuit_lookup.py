from __future__ import annotations

import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class CuitLookupError(Exception):
    def __init__(self, message: str, *, code: str = "error"):
        super().__init__(message)
        self.code = code


def normalize_cuit(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def format_cuit(digits: str) -> str:
    digits = normalize_cuit(digits)
    if len(digits) != 11:
        return digits
    return f"{digits[:2]}-{digits[2:10]}-{digits[10]}"


def is_valid_cuit(value: str) -> bool:
    digits = normalize_cuit(value)
    if len(digits) != 11 or not digits.isdigit():
        return False
    multipliers = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * m for d, m in zip(digits[:10], multipliers))
    mod = 11 - (total % 11)
    check = 0 if mod == 11 else (9 if mod == 10 else mod)
    return check == int(digits[10])


def _studio_settings():
    try:
        from apps.clients.models import StudioSettings

        return StudioSettings.load()
    except Exception:  # noqa: BLE001 — DB may not be ready in migrations/tests
        return None


def _cfg(name: str, default: str = "") -> str:
    studio = _studio_settings()
    if studio is not None:
        value = getattr(studio, name, "") or ""
        if value:
            return value
    return getattr(settings, name.upper(), default) or default


def _provider_cuitalizer(cuit: str) -> dict | None:
    api_key = _cfg("cuitalizer_api_key") or settings.CUITALIZER_API_KEY
    if not api_key:
        return None
    response = requests.post(
        "https://api.cuitalizer.com.ar/api/v1/contribuyente/consultarContribuyente",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        json={"cuit": cuit},
        timeout=20,
    )
    if response.status_code == 404:
        raise CuitLookupError("CUIT no encontrado en el padrón.")
    response.raise_for_status()
    data = response.json()
    payload = data.get("data") or data
    name = (
        payload.get("razonSocial")
        or payload.get("denominacion")
        or " ".join(
            filter(None, [payload.get("apellido"), payload.get("nombre")])
        ).strip()
    )
    if not name:
        raise CuitLookupError("La API no devolvió razón social.")
    return {
        "cuit": format_cuit(cuit),
        "name": name.strip(),
        "provider": "cuitalizer",
        "raw": payload,
    }


def _provider_http(cuit: str) -> dict | None:
    studio = _studio_settings()
    template = (
        (studio.cuit_lookup_url_template if studio else "")
        or settings.CUIT_LOOKUP_URL_TEMPLATE
    )
    if not template:
        return None
    api_key = (
        (studio.cuit_lookup_api_key if studio else "")
        or settings.CUIT_LOOKUP_API_KEY
    )
    url = template.format(cuit=cuit)
    headers = {"Accept": "application/json", "User-Agent": "fabrenaque/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    response = requests.get(url, headers=headers, timeout=20)
    if response.status_code == 404:
        raise CuitLookupError("CUIT no encontrado.")
    response.raise_for_status()
    data = response.json()
    name = (
        data.get("name")
        or data.get("razon_social")
        or data.get("razonSocial")
        or data.get("denominacion")
    )
    if not name:
        raise CuitLookupError("El proveedor HTTP no devolvió razón social.")
    return {
        "cuit": format_cuit(cuit),
        "name": str(name).strip(),
        "provider": "http",
        "raw": data,
    }


def _name_from_afip_persona(persona: dict) -> str:
    name = (
        persona.get("razonSocial")
        or persona.get("denominacion")
        or persona.get("nombre")
        or ""
    )
    if not name:
        parts = [persona.get("apellido"), persona.get("nombre")]
        name = " ".join(p for p in parts if p)
    return str(name).strip()


def _provider_afip_sdk(cuit: str) -> dict | None:
    studio = _studio_settings()
    token = (
        (studio.afip_sdk_access_token if studio else "")
        or getattr(settings, "AFIP_SDK_ACCESS_TOKEN", "")
    )
    if not token:
        return None

    try:
        from afip import Afip
    except ImportError as exc:
        raise CuitLookupError(
            "Falta instalar afip.py (`pip install afip.py`)."
        ) from exc

    tax_id = normalize_cuit(
        (studio.afip_sdk_cuit if studio and studio.afip_sdk_cuit else "")
        or getattr(settings, "AFIP_SDK_CUIT", "20409378472")
        or "20409378472"
    )
    production = bool(studio and studio.afip_sdk_production)

    afip = Afip(
        {
            "CUIT": int(tax_id),
            "access_token": token,
            "production": production,
        }
    )
    details = afip.RegisterScopeThirteen.getTaxpayerDetails(int(cuit))
    if not details:
        # En homologación muchos CUITs reales no existen; avisar claro.
        raise CuitLookupError(
            "CUIT no encontrado en el padrón (Afip SDK). "
            "En modo desarrollo solo hay contribuyentes de prueba; "
            "para CUITs reales activá producción con tu certificado en Afip SDK."
        )
    if isinstance(details, dict):
        persona = details.get("persona") or details
    else:
        persona = details
    name = _name_from_afip_persona(persona if isinstance(persona, dict) else {})
    if not name:
        raise CuitLookupError("Afip SDK no devolvió razón social.")
    return {
        "cuit": format_cuit(cuit),
        "name": name,
        "provider": "afip_sdk",
        "raw": details,
    }


def has_cuit_provider() -> bool:
    studio = _studio_settings()
    if studio and (
        studio.cuitalizer_api_key
        or studio.cuit_lookup_url_template
        or studio.afip_sdk_access_token
    ):
        return True
    return bool(
        settings.CUITALIZER_API_KEY
        or settings.CUIT_LOOKUP_URL_TEMPLATE
        or getattr(settings, "AFIP_SDK_ACCESS_TOKEN", "")
    )


def lookup_cuit(value: str) -> dict:
    cuit = normalize_cuit(value)
    if not is_valid_cuit(cuit):
        raise CuitLookupError(
            "CUIT inválido. Verificá el número (11 dígitos).",
            code="invalid",
        )

    providers = [_provider_afip_sdk, _provider_cuitalizer, _provider_http]
    tried = False
    last_error: Exception | None = None

    for provider in providers:
        try:
            result = provider(cuit)
        except CuitLookupError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("CUIT provider %s failed: %s", provider.__name__, exc)
            last_error = exc
            continue
        if result is None:
            continue
        tried = True
        return result

    if not tried:
        raise CuitLookupError(
            "Todavía no hay consulta de CUIT configurada. "
            "Podés completar la razón social a mano, o configurar Afip SDK / API "
            "en Integraciones → CUIT.",
            code="needs_config",
        )
    raise CuitLookupError(
        f"No se pudo consultar el CUIT: {last_error or 'error desconocido'}",
        code="error",
    )
