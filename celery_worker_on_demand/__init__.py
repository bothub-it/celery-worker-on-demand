import logging
import threading
import json

from time import sleep
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
from cached_property import cached_property
from kombu.utils.limits import TokenBucket
from amqp.exceptions import NotFound
from functools import partial


logger = logging.getLogger('CeleryWorkerOnDemand')
WORKERS = {}


class QueueStatus:
    def __init__(self, name, size=0, workers=[]):
        self.name = name
        self.size = size
        self.workers = workers

    @property
    def has_worker(self):
        return self.many_workers > 0

    @property
    def many_workers(self):
        return len(self.workers)

    def serializer(self):
        return {
          'name': self.name,
          'size': self.size,
          'workers': [
              worker.hostname
              for worker in self.workers
          ],
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
                    queue.workers = self.queue_workers(queue)
            else:
                sleep_time = limiter.expected_time(1)
                logger.debug(f'QueueUpdater sleeping for {sleep_time} ' +
                             'seconds...')
                sleep(sleep_time)

    def queue_workers(self, queue):
        workers = []
        inspect = self.cwod.celery_app.control.inspect(
            connection=self.cwod.connection)
        active_queues = inspect.active_queues()
        if active_queues:
            for worker_hostname, active_queues in active_queues.items():
                for q in active_queues:
                    if q.get('name') == queue.name:
                        workers.append(
                            self.cwod.WorkerStatus.get(worker_hostname),
                        )
        return workers


class QueueSizeUpdater(threading.Thread):
    def __init__(self, cwod):
        super().__init__()
        self.cwod = cwod

    def run(self):
        limiter = TokenBucket(self.cwod.queue_updater_fill_rate)
        while True:
            if limiter.can_consume():
                for queue in self.cwod.queues.values():
                    queue.size = self.queue_size(queue)

    def queue_size(self, queue):
        if hasattr(self.cwod.channel, '_size'):
            return self.cwod.channel._size(queue.name)
        try:
            return self.cwod.channel.queue_declare(
                queue=queue.name,
                passive=True,
            ).message_count
        except NotFound:
            return 0


class WorkerStatus:
    @classmethod
    def get(cls, hostname, *args, **kwargs):
        worker = WORKERS.get(hostname)
        if worker:
            return worker
        worker = cls(hostname, *args, **kwargs)
        WORKERS[hostname] = worker
        return worker

    def __init__(self, hostname, last_heartbeat_at=None,
                 last_task_received_at=None, last_task_started_at=None,
                 last_task_succeeded_at=None):
        self.hostname = hostname
        self.last_heartbeat_at = last_heartbeat_at
        self.last_task_received_at = last_task_received_at
        self.last_task_started_at = last_task_started_at
        self.last_task_succeeded_at = last_task_succeeded_at

    def serializer(self):
        return {
            'hostname': self.hostname,
            'last_heartbeat_at': self.last_heartbeat_at,
            'last_task_received_at': self.last_task_received_at,
            'last_task_started_at': self.last_task_started_at,
            'last_task_succeeded_at': self.last_task_succeeded_at,
        }


class WorkerMonitor(threading.Thread):
    def __init__(self, cwod):
        super().__init__()
        self.cwod = cwod

    def run(self):
        def handler(data):
            self.on_event(data)
        while True:
            recv = self.cwod.celery_app.events.Receiver(
                self.cwod.connection,
                handlers={'*': handler},
            )
            try:
                recv.capture(limit=None, timeout=None, wakeup=True)
            except ConnectionResetError:
                logger.warning('Reset monitor connection')

    def on_event(self, event):
        event_type = event.get('type')
        hostname = event.get('hostname')
        timestamp = event.get('timestamp')
        logger.debug(f'Event received: {event_type} / From: {hostname}')
        worker = self.cwod.WorkerStatus.get(hostname)
        if event_type == 'worker-heartbeat':
            worker.last_heartbeat_at = timestamp
        elif event_type == 'task-received':
            worker.last_task_received_at = timestamp
        elif event_type == 'task-started':
            worker.last_task_started_at = timestamp
        elif event_type == 'task-succeeded':
            worker.last_task_succeeded_at = timestamp


class UpWorker(threading.Thread):
    def __init__(self, agent, queue):
        super().__init__()
        self.agent = agent
        self.queue = queue

    def run(self):
        raise Exception('UpWorker().run() not implemented')


class DownWorker(threading.Thread):
    def __init__(self, agent, queue):
        super().__init__()
        self.agent = agent
        self.queue = queue

    def run(self):
        raise Exception('DownWorker().run() not implemented')


class Agent(threading.Thread):
    def __init__(self, cwod):
        super().__init__()
        self.cwod = cwod
        self.up_worker_th = {}
        self.down_worker_th = {}

    def run(self):
        while True:
            for queue in self.cwod.queues.values():
                if self.flag_up(queue) \
                        and not self.up_worker_th.get(queue.name):
                    logger.info(f'Up new worker to queue {queue.name}')
                    self.up_worker_th[queue.name] = self.cwod. \
                        UpWorker(self, queue)
                    self.up_worker_th[queue.name].start()
                if self.flag_down(queue) \
                        and not self.down_worker_th.get(queue.name):
                    logger.info(f'Down worker to queue {queue.name}')
                    self.down_worker_th[queue.name] = self.cwod. \
                        DownWorker(self, queue)
                    self.down_worker_th[queue.name].start()
                th_up = self.up_worker_th.get(queue.name)
                if th_up and not th_up.isAlive():
                    self.up_worker_th[queue.name] = None
                th_down = self.down_worker_th.get(queue.name)
                if th_down and not th_down.isAlive():
                    self.down_worker_th[queue.name] = None
            sleep(0.3)

    def flag_up(self, queue):
        return queue.size > 0 \
            and not queue.has_worker

    def flag_down(self, queue):
        return queue.size == 0 \
            and queue.has_worker


class APIHandler(BaseHTTPRequestHandler):
    def __init__(self, cwod, *args, **kwargs):
        self.cwod = cwod
        super().__init__(*args, **kwargs)

    def has_permission(self):
        if not self.cwod.api_basic_authorization:
            return True
        if not self.headers.get('Authorization') == \
                f'Basic {self.cwod.api_basic_authorization}':
            self.send_response(401)
            self.send_header(
                'WWW-Authenticate',
                'Basic',
            )
            self.end_headers()
            return False
        return True

    def do_GET(self):
        if not self.has_permission():
            return
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(
            bytes(
                json.dumps(
                    self.cwod.serializer(),
                    indent=2,
                ),
                'utf8',
            ),
        )


class APIServer(threading.Thread):
    def __init__(self, cwod):
        super().__init__()
        self.cwod = cwod

    def run(self):
        api_handler = partial(self.cwod.APIHandler, self.cwod)
        httpd = HTTPServer(self.cwod.api_server_address, api_handler)
        logger.info('Running API HTTP server in ' +
                    f'{self.cwod.api_server_address[0]}:' +
                    str(self.cwod.api_server_address[1]))
        httpd.serve_forever()


class CeleryWorkerOnDemand:
    QueueStatus = QueueStatus
    QueueUpdater = QueueUpdater
    QueueSizeUpdater = QueueSizeUpdater
    WorkerStatus = WorkerStatus
    WorkerMonitor = WorkerMonitor
    APIServer = APIServer
    APIHandler = APIHandler
    Agent = Agent
    UpWorker = UpWorker
    DownWorker = DownWorker

    def __init__(self, celery_app, queue_updater_fill_rate=2,
                 api_server_address=('', 8000), api_basic_authorization=None):
        self.celery_app = celery_app
        self.queue_updater_fill_rate = queue_updater_fill_rate
        self.api_server_address = api_server_address
        self.api_basic_authorization = api_basic_authorization
        self.queues = {}
        for queue in self.celery_app.conf.get('task_queues'):
            self.add_queue(queue.name)
        self.queue_updater = self.QueueUpdater(self)
        self.queue_size_updater = self.QueueSizeUpdater(self)
        self.worker_monitor = self.WorkerMonitor(self)
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
        logger.info(f'Queue {queue_name} added!')

    def run(self):
        logger.info('Running CeleryWorkerOnDemand...')
        self.queue_updater.start()
        self.queue_size_updater.start()
        self.worker_monitor.start()
        self.api_server.start()
        self.agent.start()
        self.queue_updater.join()
        self.queue_size_updater.join()
        self.worker_monitor.join()
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
            'workers': dict(
                [
                    (worker_hostname, worker.serializer())
                    for worker_hostname, worker in WORKERS.items()
                ]
            )
        }
