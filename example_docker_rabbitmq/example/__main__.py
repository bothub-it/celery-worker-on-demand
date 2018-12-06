import logging

from . import celery_app
from . import MyCeleryWorkerOnDemand


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    cbod = MyCeleryWorkerOnDemand(celery_app)
    cbod.run()
