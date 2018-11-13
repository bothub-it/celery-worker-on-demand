import docker
import logging
from time import sleep

from celery_worker_on_demand import CeleryWorkerOnDemand
from celery_worker_on_demand import UpWorker
from celery_worker_on_demand import DownWorker
from celery_worker_on_demand import Agent

from .celery_app import celery_app  # noqa:F401
from . import tasks  # noqa:F401


logger = logging.getLogger('test-docker')

docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
CONTAINERS = {}


class MyAgent(Agent):
    def flag_down(self, queue):
        return super().flag_down(queue) and CONTAINERS.get(queue.name)


class MyUpWorker(UpWorker):
    def run(self):
        container = CONTAINERS.get(self.queue.name)
        if container:
            container.start()
        else:
            container = docker_client.containers.run(
                'docker-test-app:latest',
                entrypoint='celery -A test worker -l INFO -Q '
                           f'{self.queue.name} -E',
                environment={
                    'BROKER': 'redis://redis:6379/0',
                    'BACKEND': 'redis://redis:6379/0',
                },
                network='docker-test-app',
                detach=True,
            )
            CONTAINERS[self.queue.name] = container
        while not self.queue.has_worker:
            container.reload()
            logger.debug(f'container.status is: {container.status}')
            sleep(1)


class MyDownWorker(DownWorker):
    def run(self):
        CONTAINERS[self.queue.name].stop()


class MyDemand(CeleryWorkerOnDemand):
    Agent = MyAgent
    UpWorker = MyUpWorker
    DownWorker = MyDownWorker
