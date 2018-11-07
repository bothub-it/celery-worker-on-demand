from celery import Celery
from kombu import Queue
from decouple import config


BROKER = config('BROKER', default='redis://localhost:6379/0')
BACKEND = config('BACKEND', default=BROKER)

celery_app = Celery(
    'tasks',
    broker=BROKER,
    backend=BACKEND,
)
celery_app.conf.task_queues = [
    Queue('add'),
    Queue('diff'),
]
