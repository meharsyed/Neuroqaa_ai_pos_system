"""
Cloud / production settings — Postgres, strict security, Sentry.
Run with: DJANGO_SETTINGS_MODULE=config.settings.cloud
"""

import environ
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")  # noqa: F405

DEBUG = False

DATABASES = {"default": env.db("DATABASE_URL")}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
if not CORS_ALLOWED_ORIGINS:
    # An empty list is not "wide open" — corsheaders reads it as "no browser
    # origin may ever call this API". That is a silent, confusing way for a
    # freshly deployed instance to look broken. Fail loudly at boot instead,
    # the same way a missing SECRET_KEY already does.
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS is empty. Set it in .env to the exact origin(s) the "
        "frontend is served from (e.g. https://pos.speedtechsolutions.pk) before "
        "starting this service."
    )

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

import sentry_sdk  # noqa: E402

sentry_sdk.init(
    dsn=env("SENTRY_DSN", default=""),
    traces_sample_rate=0.2,
)

STORAGES = {
    "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
    "staticfiles": {"BACKEND": "storages.backends.s3boto3.S3StaticStorage"},
}
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
