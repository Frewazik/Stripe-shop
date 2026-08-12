from pathlib import Path

from core.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
env = get_settings()

SECRET_KEY = env.secret_key
DEBUG = env.debug
ALLOWED_HOSTS = env.allowed_hosts
CSRF_TRUSTED_ORIGINS = env.csrf_trusted_origins

if not DEBUG:
    # За HTTPS-прокси Django должен доверять заголовку
    # проксирования, иначе build_absolute_uri соберёт success_url с http://.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    # unfold обязан идти перед django.contrib.admin, иначе не переопределит шаблоны.
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.catalog",
    "apps.billing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# части подключения лежат в .hosts(), а не в .username/.host напрямую
_db_host = env.database_url.hosts()[0]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": (env.database_url.path or "/").lstrip("/"),
        "USER": _db_host["username"],
        "PASSWORD": _db_host["password"],
        "HOST": _db_host["host"],
        "PORT": _db_host["port"] or 5432,
    }
}

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
