import docker
import logging
from time import sleep

from celery_worker_on_demand import CeleryWorkerOnDemand
from celery_worker_on_demand import UpWorker

from .celery_app import celery_app  # noqa:F401
from . import tasks  # noqa:F401


logger = logging.getLogger('test-docker')

docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')


class MyUpWorker(UpWorker):
    def run(self):
        container = docker_client.containers.run(
            'docker-test-app:latest',
            entrypoint=f'celery -A test worker -l INFO -Q {self.queue.name}',
            environment={
                'BROKER': 'redis://redis:6379/0',
                'BACKEND': 'redis://redis:6379/0',
            },
            volumes={
                '/var/run/docker.sock': {
                    'bind': '/var/run/docker.sock',
                    'mode': 'rw',
                },
            },
            network='docker-test-app',
            detach=True,
        )
        while not self.queue.has_worker:
            container.reload()
            logger.debug(f'container.status is: {container.status}')
            sleep(1)


class MyDemand(CeleryWorkerOnDemand):
    UpWorker = MyUpWorker
