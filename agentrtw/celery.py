import os
from celery import Celery
from dotenv import load_dotenv

# 首先加载 .env 文件
load_dotenv()

# 设置 Django settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agentrtw.settings')

app = Celery('agentrtw')

# 从 Django settings 加载配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """
    This is a debug task that prints the name of the current task.
    """
    print(f'Request: {self.request!r}')