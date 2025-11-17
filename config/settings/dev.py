# Development settings
from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Development database (SQLite for simplicity)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Development CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
]

# Development logging
LOGGING["handlers"]["file"]["filename"] = BASE_DIR / "logs" / "dev.log"

# Disable security for development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
