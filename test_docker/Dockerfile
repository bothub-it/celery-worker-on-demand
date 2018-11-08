FROM python:3.6-alpine

ENV WORKDIR /home/app
WORKDIR ${WORKDIR}

RUN pip install pipenv

COPY ./test_docker/ .
COPY . ./celery-worker-on-demand/
RUN pipenv install --system
