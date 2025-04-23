import os

from celery import Celery

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE', 'agentrtw.settings')

app = Celery('agentrtw')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

def debug_task(self):
    """
    This is a debug task that prints the name of the current task.
    """
    print(f'Request: {self.request!r}')
