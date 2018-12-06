from decouple import config
from celery import Celery
from kombu import Queue


BROKER = config('BROKER', default='amqp://cwod:cwod@localhost:5672/rabbit')
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
