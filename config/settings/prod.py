# Production settings
from .base import *

DEBUG = False

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",")]
)

# Security settings for production
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Production logging
LOGGING["handlers"]["file"]["filename"] = BASE_DIR / "logs" / "prod.log"
LOGGING["handlers"]["file"]["level"] = "WARNING"

# Production CORS (should be restrictive)
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS", cast=lambda v: [s.strip() for s in v.split(",")]
)

# Production file storage (should use S3)
USE_S3 = config("USE_S3", default=True, cast=bool)

# Production Redis settings
CHANNEL_LAYERS["default"]["CONFIG"]["hosts"] = [
    (config("REDIS_HOST"), config("REDIS_PORT", cast=int))
]

# Production Celery
CELERY_BROKER_URL = config("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND")
