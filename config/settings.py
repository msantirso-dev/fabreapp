"""Django settings for Estudio Contable (fabrenaque)."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    GOOGLE_CALENDAR_ENABLED=(bool, False),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-key-change-me")
DEBUG = env("DEBUG")

# Siempre incluir el dominio de producción para evitar Bad Request (400) / DisallowedHost
# detrás de Coolify cuando faltan variables de entorno.
_default_hosts = [
    "localhost",
    "127.0.0.1",
    "app.fabregad.com.ar",
]
ALLOWED_HOSTS = list(
    dict.fromkeys(
        [h.strip() for h in env.list("ALLOWED_HOSTS", default=_default_hosts) if h.strip()]
        + _default_hosts
    )
)

APP_BASE_URL = env("APP_BASE_URL", default="https://app.fabregad.com.ar")
APPLICATION_NAME = env("APPLICATION_NAME", default="fabrenaque")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.accounts",
    "apps.clients",
    "apps.deadlines",
    "apps.calendar_sync",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ar"
TIME_ZONE = env("GOOGLE_CALENDAR_TIMEZONE", default="America/Argentina/Buenos_Aires")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "login"

_default_csrf = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://app.fabregad.com.ar",
]
CSRF_TRUSTED_ORIGINS = list(
    dict.fromkeys(
        [o.strip() for o in env.list("CSRF_TRUSTED_ORIGINS", default=_default_csrf) if o.strip()]
        + _default_csrf
    )
)

# Coolify / reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# Google Calendar — shared calendar only (no per-user event copies)
GOOGLE_CALENDAR_ENABLED = env("GOOGLE_CALENDAR_ENABLED")
GOOGLE_SERVICE_ACCOUNT_FILE = env("GOOGLE_SERVICE_ACCOUNT_FILE", default="")
GOOGLE_DELEGATED_USER = env("GOOGLE_DELEGATED_USER", default="")
GOOGLE_SHARED_CALENDAR_ID = env("GOOGLE_SHARED_CALENDAR_ID", default="")
GOOGLE_SHARED_CALENDAR_NAME = env(
    "GOOGLE_SHARED_CALENDAR_NAME",
    default="Vencimientos – Estudio Contable",
)
GOOGLE_CALENDAR_TIMEZONE = TIME_ZONE
GOOGLE_CALENDAR_SCHEMA_VERSION = env("GOOGLE_CALENDAR_SCHEMA_VERSION", default="1")

# OAuth (recomendado): conectar cuenta Google desde la UI
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default="")
GOOGLE_OAUTH_REDIRECT_URI = env(
    "GOOGLE_OAUTH_REDIRECT_URI",
    default=f"{APP_BASE_URL.rstrip('/')}/integraciones/google/callback/",
)

# Prepared for future Google Calendar push notifications (not used in MVP)
GOOGLE_CALENDAR_WEBHOOK_URL = env("GOOGLE_CALENDAR_WEBHOOK_URL", default="")
GOOGLE_CALENDAR_CHANNEL_TOKEN = env("GOOGLE_CALENDAR_CHANNEL_TOKEN", default="")

# CUIT lookup (autocompletar razón social)
CUITALIZER_API_KEY = env("CUITALIZER_API_KEY", default="")
CUIT_LOOKUP_URL_TEMPLATE = env("CUIT_LOOKUP_URL_TEMPLATE", default="")
CUIT_LOOKUP_API_KEY = env("CUIT_LOOKUP_API_KEY", default="")
AFIP_SDK_ACCESS_TOKEN = env("AFIP_SDK_ACCESS_TOKEN", default="")
AFIP_SDK_CUIT = env("AFIP_SDK_CUIT", default="20409378472")
