"""
Development settings — Postgres via docker-compose, debug toolbar, relaxed CORS.
Run with: DJANGO_SETTINGS_MODULE=config.settings.dev
"""

import environ

from .base import *  # noqa: F401, F403

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")  # noqa: F405

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="pos_dev"),
        "USER": env("POSTGRES_USER", default="pos_user"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="pos_password"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "DEBUG"},
}
