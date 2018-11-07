from .app import celery_app


@celery_app.task
def add(x, y):
    return x + y


@celery_app.task
def diff(x, y):
    return x - y
