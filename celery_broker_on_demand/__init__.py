import logging
from time import sleep

from cached_property import cached_property
from kombu.utils.limits import TokenBucket


logger = logging.getLogger('CeleryBrokerOnDemand')


class CeleryBrokerOnDemand:
    INSPECT_METHODS = ('stats', 'active_queues', 'registered', 'scheduled',
                       'active', 'reserved', 'revoked', 'conf')

    def __init__(self, celery_app):
        self.celery_app = celery_app

    @cached_property
    def connection(self):
        logger.debug('Getting connection...')
        return self.celery_app.connection(heartbeat=False)

    @property
    def channel(self):
        return self.connection.default_channel

    @cached_property
    def consumer(self):
        logger.debug('Getting consumer...')
        return self.celery_app.amqp.TaskConsumer(
            self.channel,
            callbacks=[
                self.on_message,
            ],
        )

    def run(self):
        logger.info('Running Celery Broker On Demand...')
        limiter = TokenBucket(1)
        with self.consumer:
            while True:
                try:
                    if limiter.can_consume(1):
                        logger.debug('Drain events...')
                        self.connection.drain_events()
                    else:
                        sleep_time = limiter.expected_time(1)
                        logger.debug(f'Sleeping for {sleep_time} seconds...')
                        sleep(sleep_time)
                except Exception as e:
                    logger.exception(e)
                    raise e

    def on_message(self, task_args, message):
        logger.info(f"""---
Message received
| Task Args: {task_args}
| Message: {message}
---""")
        routing_key = message.delivery_info.get('routing_key')
        if self.flag_up(routing_key):
            self.up_worker(routing_key)
        elif self.flag_down(routing_key):
            self.down_worker(routing_key)
        message.requeue()

    def flag_up(self, queue):
        return not self.exists_worker_to_queue(queue)

    def flag_down(self, queue):
        return False

    def up_worker(self, queue):
        logger.debug(f'Up worker: {queue}')

    def down_worker(self, queue):
        logger.debug(f'Down worker: {queue}')

    def exists_worker(self):
        pass

    def exists_worker_to_queue(self, queue_name):
        logger.debug(f'Checking if exists some worker to {queue_name} ' +
                     'queue...')

        found = False

        inspect = self.celery_app.control.inspect()
        active_queues = inspect.active_queues()
        if active_queues:
            for worker_hostname, active_queues in active_queues.items():
                for queue in active_queues:
                    if queue.get('name') == queue_name:
                        logger.debug(f'Worker to {queue_name} found: ' +
                                     '{worker_hostname}')
                        found = True

        if not found:
            logger.debug(f'Worker to {queue_name} not found!')

        return found
