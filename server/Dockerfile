FROM python:3.8.2-slim-buster

LABEL maintainer="dev@togglecorp.com"

ENV PYTHONUNBUFFERED 1

WORKDIR /code


RUN apt-get update -y \
    && apt-get install -y libpq-dev gcc

COPY ./requirements.txt /code/requirements.txt

RUN python3 -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get autoremove

COPY . /code/

CMD ./deploy/scripts/run_prod.sh
