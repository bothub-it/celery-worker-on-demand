import logging
import docker
from time import sleep

from celery_broker_on_demand import CeleryBrokerOnDemand

from .app import celery_app


logger = logging.getLogger('test-docker')


class MyDemand(CeleryBrokerOnDemand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker_client = docker.DockerClient(
            base_url='unix://var/run/docker.sock',
        )

    def up_worker(self, queue):
        container = self.docker_client.containers.run(
            'docker-test-app:latest',
            entrypoint='celery -A test.app worker -l INFO',
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
            sleep(.5)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    cbod = MyDemand(celery_app)
    cbod.run()
