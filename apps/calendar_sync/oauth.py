from __future__ import annotations

import logging
import os
from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from .models import GoogleCalendarConnection

logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


class GoogleOAuthNotConfigured(Exception):
    pass


def _studio_oauth() -> dict:
    """Lee OAuth desde DB (formulario web) con fallback a settings/.env."""
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
    redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    app_base_url = settings.APP_BASE_URL

    try:
        from apps.clients.models import StudioSettings

        studio = StudioSettings.load()
        if studio.google_oauth_client_id:
            client_id = studio.google_oauth_client_id
        if studio.google_oauth_client_secret:
            client_secret = studio.google_oauth_client_secret
        if studio.google_oauth_redirect_uri:
            redirect_uri = studio.google_oauth_redirect_uri
        if studio.app_base_url:
            app_base_url = studio.app_base_url.rstrip("/")
    except Exception:  # noqa: BLE001
        logger.debug("StudioSettings OAuth unavailable; using env settings")

    if not redirect_uri and app_base_url:
        redirect_uri = f"{app_base_url.rstrip('/')}/integraciones/google/callback/"

    return {
        "client_id": client_id or "",
        "client_secret": client_secret or "",
        "redirect_uri": redirect_uri or "",
        "app_base_url": app_base_url or "",
    }


def oauth_is_configured() -> bool:
    cfg = _studio_oauth()
    return bool(cfg["client_id"] and cfg["client_secret"] and cfg["redirect_uri"])


def _allow_http_localhost() -> None:
    cfg = _studio_oauth()
    redirect = cfg["redirect_uri"]
    if settings.DEBUG or redirect.startswith("http://"):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def _client_config() -> dict:
    cfg = _studio_oauth()
    if not (cfg["client_id"] and cfg["client_secret"]):
        raise GoogleOAuthNotConfigured(
            "Completá Client ID y Client Secret en el formulario de Google."
        )
    if not cfg["redirect_uri"]:
        raise GoogleOAuthNotConfigured(
            "Completá la URI de redirección en el formulario de Google."
        )
    return {
        "web": {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [cfg["redirect_uri"]],
        }
    }


def build_oauth_flow(*, state: str | None = None) -> Flow:
    _allow_http_localhost()
    cfg = _studio_oauth()
    flow = Flow.from_client_config(
        _client_config(),
        scopes=GOOGLE_CALENDAR_SCOPES,
        state=state,
    )
    flow.redirect_uri = cfg["redirect_uri"]
    return flow


def credentials_from_connection(connection: GoogleCalendarConnection) -> Credentials:
    cfg = _studio_oauth()
    expiry = None
    if connection.token_expiry:
        expiry = connection.token_expiry.astimezone(dt_timezone.utc).replace(tzinfo=None)

    creds = Credentials(
        token=connection.access_token or None,
        refresh_token=connection.refresh_token or None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=GOOGLE_CALENDAR_SCOPES,
        expiry=expiry,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        connection.access_token = creds.token or ""
        if creds.expiry:
            connection.token_expiry = timezone.make_aware(
                creds.expiry, timezone=dt_timezone.utc
            )
        connection.save(update_fields=["access_token", "token_expiry", "updated_at"])
    return creds


def save_connection_from_credentials(
    *,
    credentials: Credentials,
    user,
    google_email: str = "",
) -> GoogleCalendarConnection:
    GoogleCalendarConnection.objects.filter(is_active=True).update(is_active=False)

    expiry = None
    if credentials.expiry:
        expiry = timezone.make_aware(credentials.expiry, timezone=dt_timezone.utc)

    connection = GoogleCalendarConnection.objects.create(
        connected_by=user,
        google_email=google_email,
        access_token=credentials.token or "",
        refresh_token=credentials.refresh_token or "",
        token_expiry=expiry,
        scopes=" ".join(credentials.scopes or GOOGLE_CALENDAR_SCOPES),
        shared_calendar_name=settings.GOOGLE_SHARED_CALENDAR_NAME,
        is_active=True,
    )
    return connection


def fetch_google_email(credentials: Credentials) -> str:
    service = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
    info = service.userinfo().get().execute()
    return info.get("email", "")


def build_calendar_service_from_oauth():
    connection = GoogleCalendarConnection.get_active()
    if not connection:
        return None, None
    creds = credentials_from_connection(connection)
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return service, connection
