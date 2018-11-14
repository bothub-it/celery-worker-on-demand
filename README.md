# Celery Worker On Demand

Up and down Celery workers on demand.

## Examples

Check the [example](https://github.com/Ilhasoft/celery-worker-on-demand/tree/master/example_docker) using a Docker container to up and down Celery workers.

## Usage

### Dependencies

- Python 3.6
- Celery 4.2.1 or higher
- Your [Celery Application](http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html#application)
- celery_worker_on_demand Python package
  ```bash
  pip install celery-worker-on-demand
  ```

### Create a custom Class extended from CeleryWorkerOnDemand

Create a custom Class extended from CeleryWorkerOnDemand to customize Agent, UpWorker and DownWorker classes.

```python
from celery_worker_on_demand import CeleryWorkerOnDemand
from celery_worker_on_demand import Agent
from celery_worker_on_demand import UpWorker
from celery_worker_on_demand import DownWorker


class MyDemand(CeleryWorkerOnDemand):
    # Customize Agent methods to apply new rules to up (flag_up) and down (flag_down) Celery workers
    Agent = Agent
    # Overide UpWorker run method with your script to up new Celery worker
    UpWorker = UpWorker
    # Overide DownWorker run method with your script to up new Celery worker
    DownWorker = DownWorker
```

### Implement your up and down Celery worker script

You need overide UpWorker and DownWorker run method with your custom script to up and down Celery worker.

```python
from celery_worker_on_demand import CeleryWorkerOnDemand
from celery_worker_on_demand import UpWorker
from celery_worker_on_demand import DownWorker


class MyUpWorker(UpWorkerU):
    def run(self):
        # Use self.cwod to retrieve CeleryWorkerOnDemand instance;
        # Use self.queue to retrieve QueueStatus instance with all queue information;
        ... Your script here


class MyDownWorker(DownWorker):
    def run(self):
        # Use self.cwod to retrieve CeleryWorkerOnDemand instance;
        # Use self.queue to retrieve QueueStatus instance with all queue information;
        ... Your script here


class MyDemand(CeleryWorkerOnDemand):
    UpWorker = MyUpWorker
    DownWorker = MyDownWorker
```

### Create a runnable Python file

Create a runnable Python file like below, to run like a service.

```python
#!/bin/env/python
from .cwod import MyDemand
from .celery_app import celery_app


# Run Celery Worker On Demand service
MyDemand(celery_app).run()
```

## Customize up and down rules

To customize up and down flag you just need overide Agent methods `flag_up` and `flag_down`.

```python
from celery_worker_on_demand import CeleryWorkerOnDemand
from celery_worker_on_demand import Agent


class MyAgent(Agent):
    # When returns True, the UpWorker.run() method is executed
    def flag_up(self, queue):
        # queue is a QueueStatus instance
        return super().flag_up(queue)

    # When returns True, the DownWorker.run() method is executed
    def flag_down(self, queue):
        # queue is a QueueStatus instance
        return super().flag_down(queue)


class MyDemand(CeleryWorkerOnDemand):
    Agent = MyAgent
```

## API

### class CeleryWorkerOnDemand

#### constructor

- **celery_app** (arg): Your [Celery Application](http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html#application) instance.
- **queue_updater_fill_rate** (kwarg): Times to update per second queue status. Default is `2`.
- **api_server_address** (kwarg): Tuple with address and port to serve API. Default is `('', 8000)`.

#### attributes

- **celery_app**: Your Celery Application instance
- **queue_updater_fill_rate**: Times to update per second queue status.
- **api_server_address**: Tuple with address and port to serve API.
- **queues**: Queue dictionary - key is the queue name and value is a QueueStatus instance.
- **queue_updater**: Thread instance of QueueUpdater
- **worker_monitor**: Thread instance of WorkerMonitor
- **api_server**: Thread instance of APIServer
- **agent**: Thread instance of Agent

#### properties

- **connection**: Cached property, returns main broker connection without heartbeat.
- **channel**: Cached property, returns default channel.

#### .add_queue(queue_name) method

- **queue_name** (arg): Queue name.

Add new queue to observer.

#### .run() method

Start the Celery Worker On Demand service.

#### .serializer() method

Returns a JSON serializable dictionary that represents the current state of instance.

### class Agent

#### constructor

- **cwod** (arg): CeleryWorkerOnDemand instance.

#### .run() method

Watch current state of application to up and down workers.

#### flag_up(queue) method

- **queue** (arg): QueueStatus instance.

When returns True, the UpWorker.run() method is executed.

#### flag_down(queue) method

- **queue** (arg): QueueStatus instance.

When returns True, the DownWorker.run() method is executed

### class UpWorker

#### constructor

- **agent** (arg): Agent instance.
- **queue** (arg): QueueStatus instance.

#### .run() method

Python script to up new worker to queue.

### class DownWorker

#### constructor

- **agent** (arg): Agent instance.
- **queue** (arg): QueueStatus instance.

#### .run() method

Python script to down queue's worker(s).

### class QueueStatus

#### constructor

- **name** (arg): Queue name.
- **size** (kwarg): Current queue size, default is `0`.
- **workers** (kwarg): List of WorkerStatus instance, default is a empty list.

#### attributes

- **name**: Queue name.
- **size**: Current queue size.
- **workers**: List of WorkerStatus instance.

#### properties

- **has_worker**: Returns True when queue has worker.
- **many_workers**: Returns how many workers the queue have.

#### .serializer() method

Returns a JSON serializable dictionary that represents the current state of instance.

### class WorkerStatus

#### .get(hostname, *, **) class method

- **hostname** (arg): Worker hostname.
- **\***: args passed to WorkerStatus constructor.
- **\*\***: kwargs passed to WorkerStatus constructor.

Returns a cached WorkerStatus instance relative to hostname.

#### constructor

- **hostname** (arg): Worker hostname.
- **last_heartbeat_at** (kwarg): Timestamp of last hearbeat. Default is `None`.
- **last_task_received_at** (kwarg): Timestamp of last task received. Default is `None`.
- **last_task_started_at** (kwarg): Timestamp of last task started. Default is `None`.
- **last_task_succeeded_at** (kwarg): Timestamp of last task succeeded. Default is `None`.

#### attributes

- **hostname** (arg): Worker hostname.
- **last_heartbeat_at** (kwarg): Timestamp of last hearbeat.
- **last_task_received_at** (kwarg): Timestamp of last task received.
- **last_task_started_at** (kwarg): Timestamp of last task started.
- **last_task_succeeded_at** (kwarg): Timestamp of last task succeeded.

#### .serializer() method

Returns a JSON serializable dictionary that represents the current state of instance.
