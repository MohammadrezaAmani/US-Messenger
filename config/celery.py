import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("chat_service")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


# Define periodic tasks
app.conf.beat_schedule = {
    "cleanup-expired-tokens": {
        "task": "apps.accounts.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "cleanup-old-notifications": {
        "task": "apps.notifications.tasks.cleanup_old_notifications",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    "generate-daily-stats": {
        "task": "apps.chat.tasks.generate_daily_stats",
        "schedule": crontab(hour=4, minute=0),  # Daily at 4 AM
    },
}
