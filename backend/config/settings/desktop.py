"""
Desktop (Tauri) settings — SQLite, no network dependencies, offline-first.
Run with: DJANGO_SETTINGS_MODULE=config.settings.desktop
"""
from .base import *  # noqa: F401, F403
import environ
from pathlib import Path

env = environ.Env()
# Load .env if present — for local dev. Tauri sets env vars directly at runtime.
_env_file = BASE_DIR / ".env"  # noqa: F405
if _env_file.exists():
    environ.Env.read_env(_env_file)

# Read DEBUG from .env so local dev (DEBUG=True) gets static files from the dev
# server, while the real Tauri production binary sets DEBUG=False via its own env.
DEBUG = env.bool("DEBUG", default=False)

# SQLite stored in the OS app-data dir; Tauri sets POS_DATA_DIR at runtime.
DATA_DIR = Path(env("POS_DATA_DIR", default=str(BASE_DIR / "data")))  # noqa: F405
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "pos.db",
    }
}

# When running locally (DEBUG=True) allow the Vite dev server too.
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [
        "tauri://localhost",
        "https://tauri.localhost",
    ]

# Tighter token lifetimes for desktop (device is local, no shared session risk)
SIMPLE_JWT = {
    **SIMPLE_JWT,  # noqa: F405
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),  # noqa: F405
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}
