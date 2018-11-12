import logging
import threading
import json
from time import sleep
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

from cached_property import cached_property
from kombu.utils.limits import TokenBucket


logger = logging.getLogger('CeleryWorkerOnDemand')


class QueueStatus:
    def __init__(self, name, size=0, many_workers=0):
        self.name = name
        self.size = size
        self.many_workers = many_workers

    @property
    def has_worker(self):
        return self.many_workers > 0

    def serializer(self):
        return {
          'name': self.name,
          'size': self.size,
          'many_workers': self.many_workers,
          'has_worker': self.has_worker,
        }


class QueueUpdater(threading.Thread):
    def __init__(self, cwod):
        super().__init__()
        self.cwod = cwod

    def run(self):
        limiter = TokenBucket(self.cwod.queue_updater_fill_rate)
        while True:
            if limiter.can_consume():
                for queue in self.cwod.queues.values():
                    queue.size = self.queue_size(queue)
                    queue.many_workers = self.queue_many_workers(queue)
            else:
                sleep_time = limiter.expected_time(1)
                logger.debug(f'Sleeping for {sleep_time} seconds...')
                sleep(sleep_time)

    def queue_size(self, queue):
        return self.cwod.channel._size(queue.name)

    def queue_many_workers(self, queue):
        logger.debug(
            f'Checking if exists some worker to {queue.name} queue...')
        found = 0
        inspect = self.cwod.celery_app.control.inspect()
        active_queues = inspect.active_queues()
        if active_queues:
            for worker_hostname, active_queues in active_queues.items():
                for q in active_queues:
                    if q.get('name') == queue.name:
                        logger.debug(
                            f'Worker to {queue.name} found: {worker_hostname}')
                        found += 1
        if found == 0:
            logger.debug(f'Worker to {queue.name} not found!')
        return found


class UpWorker(threading.Thread):
    def __init__(self, agent, queue):
        super().__init__()
        self.agent = agent
        self.queue = queue

    def run(self):
        logger.debug(f'Uping new worker to queue {self.queue.name}')
        raise Exception('UpWorker().run() not implemented')


class Agent(threading.Thread):
    def __init__(self, cwod):
        super().__init__()
        self.cwod = cwod
        self.up_worker_th = {}

    def run(self):
        while True:
            for queue in self.cwod.queues.values():
                if self.flag_up(queue):
                    logger.info(f'Up new worker to queue {queue.name}')
                    self.up_worker_th[queue.name] = self.cwod. \
                        UpWorker(self, queue)
                    self.up_worker_th[queue.name].start()
                th = self.up_worker_th.get(queue.name)
                if th and not th.isAlive():
                    self.up_worker_th[queue.name] = None
            sleep(.2)

    def flag_up(self, queue):
        return queue.size > 0 \
            and not queue.has_worker \
            and not self.up_worker_th.get(queue.name)


class APIServer(threading.Thread):
    def __init__(self, cwod):
        super().__init__()
        self.cwod = cwod

    def run(self):
        cwod = self.cwod

        class APIHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(
                    bytes(
                        json.dumps(
                            cwod.serializer(),
                            indent=2,
                        ),
                        'utf8',
                    ),
                )
        httpd = HTTPServer(self.cwod.api_server_address, APIHandler)
        httpd.serve_forever()


class CeleryWorkerOnDemand:
    QueueStatus = QueueStatus
    QueueUpdater = QueueUpdater
    APIServer = APIServer
    Agent = Agent
    UpWorker = UpWorker

    def __init__(self, celery_app, queue_updater_fill_rate=2,
                 api_server_address=('', 8000)):
        self.celery_app = celery_app
        self.queue_updater_fill_rate = queue_updater_fill_rate
        self.api_server_address = api_server_address
        self.queues = {}
        for queue in self.celery_app.conf.get('task_queues'):
            self.add_queue(queue.name)
        self.queue_updater = self.QueueUpdater(self)
        self.api_server = self.APIServer(self)
        self.agent = self.Agent(self)

    @cached_property
    def connection(self):
        logger.debug('Getting connection...')
        return self.celery_app.connection(heartbeat=False)

    @cached_property
    def channel(self):
        return self.connection.default_channel

    def add_queue(self, queue_name):
        self.queues[queue_name] = self.QueueStatus(queue_name)

    def run(self):
        self.queue_updater.start()
        self.api_server.start()
        self.agent.start()
        self.queue_updater.join()
        self.api_server.join()
        self.agent.join()

    def serializer(self):
        return {
            'queues': dict(
                [
                    (queue_name, queue.serializer())
                    for queue_name, queue in self.queues.items()
                ]
            ),
        }
