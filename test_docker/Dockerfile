FROM python:3.6-alpine

ENV WORKDIR /home/app
WORKDIR ${WORKDIR}

RUN pip install pipenv

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
COPY ./test_docker/ .
COPY . ./celery-broker-on-demand/
RUN pipenv install --system
