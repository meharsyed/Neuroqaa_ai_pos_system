"""
Base settings shared across all environments.
Never import this file directly in manage.py — always use a concrete env file.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Load .env from the backend directory if it exists.
# This lets desktop.py and any settings module work without manually setting
# env vars in the shell. Individual env files (dev.py) re-read it for overrides.
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    environ.Env.read_env(_env_file)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

AUTH_USER_MODEL = "accounts.User"

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "import_export",
    "simple_history",
    "django_filters",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.catalog",
    "apps.sales",
    "apps.config",
    "apps.customers",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    # A login page on the open internet is brute-forced by bots within days of
    # the DNS record appearing. "login" is applied to LoginView by scope; the
    # anon/user rates are a backstop for everything else.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "1000/min",
        # Ten attempts a minute is far more than a cashier mistyping a password
        # and far less than a password list makes progress with.
        "login": "10/min",
        # No login gates this one, so it is capped harder, by IP alone —
        # see apps/sales/public_views.py.
        "public_receipt": "20/min",
    },
}

# JWT
#
# The refresh token never reaches JavaScript: LoginView and CookieTokenRefreshView
# (apps/accounts/views.py) strip it out of the response body and set it as an
# httpOnly cookie instead, so an XSS in the app cannot read it out of
# localStorage. BLACKLIST_AFTER_ROTATION means a stolen or logged-out refresh
# token stops working immediately rather than staying valid for its full
# lifetime — see LogoutView, which blacklists on sign-out.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# The refresh-token cookie. Scoped to the one path that ever reads it, so it
# is never sent on ordinary API calls. SECURE follows DEBUG by default —
# overridden explicitly wherever that is wrong (see cloud.py / desktop.py).
JWT_REFRESH_COOKIE_NAME = "refresh_token"
JWT_REFRESH_COOKIE_PATH = "/api/auth/"
JWT_REFRESH_COOKIE_SAMESITE = "Lax"
JWT_REFRESH_COOKIE_SECURE = not DEBUG

# Cookies only cross an origin at all when the browser is told the request
# may carry credentials — required for the refresh cookie above to work from
# the Vite dev server (a different origin than the API) and from any split
# frontend/backend deployment.
CORS_ALLOW_CREDENTIALS = True

# OpenAPI
SPECTACULAR_SETTINGS = {
    "TITLE": "Neuroqaa POS API",
    "DESCRIPTION": "Point of Sale system API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Admin branding
ADMIN_SITE_HEADER = "Neuroqaa POS Admin"
ADMIN_SITE_TITLE = "Neuroqaa POS"
ADMIN_INDEX_TITLE = "Administration"
