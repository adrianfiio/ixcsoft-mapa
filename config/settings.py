from pathlib import Path
from urllib.parse import urlparse
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


WEB_URL = os.getenv("WEB_URL", "").strip().rstrip("/")
WEB_HOST = urlparse(WEB_URL).hostname if WEB_URL else ""

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "inseguro-apenas-desenvolvimento")
APP_VERSION = os.getenv("APP_VERSION", "0.9.3")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = [WEB_HOST] if WEB_HOST else ["localhost", "127.0.0.1"]

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
if not CSRF_TRUSTED_ORIGINS and WEB_URL:
    CSRF_TRUSTED_ORIGINS = [WEB_URL]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "false").lower() == "true"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "django_celery_beat",
    "drf_spectacular",
    "apps.core",
    "apps.access.apps.AccessConfig",
    "apps.ixc_integration.apps.IxcIntegrationConfig",
    "apps.olt_integration",
    "apps.optical",
    "apps.network_map",
    "apps.alerts",
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
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [{
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
}]

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.getenv("POSTGRES_DB", "ixcsoft_mapa"),
        "USER": os.getenv("POSTGRES_USER", "ixcsoft"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "ixcsoft_dev"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/assets/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "AFService Map API",
    "DESCRIPTION": "API do sistema de monitoramento de rede óptica.",
    "VERSION": APP_VERSION,
}

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
if not CORS_ALLOWED_ORIGINS and WEB_URL:
    CORS_ALLOWED_ORIGINS = [WEB_URL]

CELERY_BEAT_SCHEDULE = {
    "synchronize-all-ixc-configurations": {
        "task": "apps.ixc_integration.tasks.synchronize_all_ixc_configurations",
        "schedule": 300.0,
    },
}

FIELD_ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY", "")

STATICFILES_DIRS = [
    BASE_DIR / "static",
]
