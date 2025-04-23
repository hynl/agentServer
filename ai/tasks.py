import time

from celery import shared_task

@shared_task
def debug_task_test(message, duration = 5):
    print(f"------CELERY DEBUG TASK------")
    print(f'Request: {message!r}')
    print(f"Duration: {duration}")
    time.sleep(duration)
    print(f"Task Complete")