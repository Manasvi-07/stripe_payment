import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stripe_project.settings")

app = Celery("stripe_project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'sync-stripe-every-hour': {
        'task': 'payments.tasks.send_subscription_reminders',
        'schedule': crontab(hour=5, minute=10),
    },
}