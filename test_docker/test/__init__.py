import docker
import logging
from time import sleep

from celery_worker_on_demand import CeleryWorkerOnDemand

from .celery_app import celery_app  # noqa:F401
from . import tasks  # noqa:F401


logger = logging.getLogger('test-docker')


class MyDemand(CeleryWorkerOnDemand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_client = docker.DockerClient(
            base_url='unix://var/run/docker.sock',
        )

    def up_worker(self, queue):
        container = self.docker_client.containers.run(
            'docker-test-app:latest',
            entrypoint=f'celery -A test worker -l INFO -Q {queue}',
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
        while container.status != 'running' or \
                not self.exists_worker_to_queue(queue):
            container.reload()
            logger.debug(f'container.status is: {container.status}')
            if container.status in ['running']:
                pass
            sleep(.25)
