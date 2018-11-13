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

Create a runnable Python file like above, to create a service.

```python
#!/bin/env/python
from .cwod import MyDemand
from .celery_app import celery_app


# Run Celery Worker On Demand service
MyDemand(celery_app).run()
```
