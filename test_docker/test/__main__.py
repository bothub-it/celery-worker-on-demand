import logging

from . import celery_app
from . import MyDemand


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    cbod = MyDemand(celery_app)
    cbod.run()
