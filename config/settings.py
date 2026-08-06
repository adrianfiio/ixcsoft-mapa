from pathlib import Path
from urllib.parse import urlparse
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


WEB_URL = os.getenv("WEB_URL", "").strip().rstrip("/")
WEB_HOST = urlparse(WEB_URL).hostname if WEB_URL else ""

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "inseguro-apenas-desenvolvimento")

# Duas versões independentes dentro do mesmo repositório/deploy: a
# plataforma (Dashboard, Financeiro, Visão geral, Superadmin, empresas,
# usuários) e o mapa (editor cartográfico, Rack/Torre, Canvas 2D,
# fusões, popups, SNMP/monitoramento visual, enlaces). Cada trilha tem
# seu próprio changelog (CHANGELOG_PLATFORM.md/CHANGELOG_MAP.md), tag
# (platform-vX.Y.Z/map-vX.Y.Z) e release — nunca mais uma tag vX.Y.Z
# genérica. Ver VERSIONS.md. APP_VERSION continua existindo só por
# compatibilidade com código legado que ainda lê essa variável — ela é
# sempre igual a PLATFORM_VERSION, nunca uma versão própria.
PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.83.0"))
APP_VERSION = PLATFORM_VERSION
MAP_VERSION = os.getenv("MAP_VERSION", "0.75.50")

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
    "apps.snmp_monitoring",
    "apps.billing.apps.BillingConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.billing.middleware.SubscriptionAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/carregando/"
LOGOUT_REDIRECT_URL = "/login/"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
            "apps.core.context_processors.company_navigation",
            "apps.core.context_processors.app_version",
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

SNMP_STATUS_POLL_SECONDS = float(os.getenv("SNMP_STATUS_POLL_SECONDS", "30"))
SNMP_STATUS_STALE_SECONDS = int(os.getenv("SNMP_STATUS_STALE_SECONDS", "180"))

CELERY_BEAT_SCHEDULE = {
    "synchronize-all-ixc-configurations": {
        "task": "apps.ixc_integration.tasks.synchronize_all_ixc_configurations",
        "schedule": 60.0,
    },
    "synchronize-ixc-pppoe-statuses": {
        "task": "apps.ixc_integration.tasks.synchronize_ixc_pppoe_statuses",
        "schedule": 300.0,
    },
    "poll-snmp-status": {
        "task": "apps.snmp_monitoring.tasks.poll_snmp_status",
        "schedule": SNMP_STATUS_POLL_SECONDS,
    },
    "generate-monthly-invoices": {
        "task": "apps.billing.tasks.generate_monthly_invoices",
        "schedule": 3600.0,
    },
    "mark-overdue-invoices": {
        "task": "apps.billing.tasks.mark_overdue_invoices",
        "schedule": 3600.0,
    },
    "purge-old-canceled-invoices": {
        "task": "apps.billing.tasks.purge_old_canceled_invoices",
        "schedule": 86400.0,
    },
}

FIELD_ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY", "")

# Monitoramento SNMP (Telegraf/InfluxDB) — infraestrutura mantida fora
# deste repositório, ver docs/releases/. Nunca commitar o token de verdade
# aqui nem em nenhum arquivo: só via variável de ambiente no servidor.
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://monitor-influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "AFService")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "mapa_metrics")
SNMP_TELEGRAF_CONTAINER = os.getenv("SNMP_TELEGRAF_CONTAINER", "monitor-telegraf")
SNMP_CONF_DIR = os.getenv("SNMP_CONF_DIR", "") or (BASE_DIR / "equipamentos_ativos_snmp")

# SMTP padrão da plataforma (uso interno/administrativo). Empresas configuram
# o próprio SMTP em "Minha administração" — este aqui não é usado como
# reserva para elas.
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@afservicemap.local")

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Com DEBUG=false (produção), o logging padrão do Django só manda erro 500
# por e-mail (mail_admins) — sem ADMINS configurado, o traceback simplesmente
# some, sem aparecer em lugar nenhum. Isso sempre imprime no console (logs do
# container), independente de DEBUG, para dar pra investigar erro em produção.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
