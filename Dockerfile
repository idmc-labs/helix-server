FROM python:3.8.2-buster AS server

LABEL maintainer="dev@togglecorp.com"

ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY ./Pipfile* /code
RUN python3 -m pip install --upgrade pip \
    && pipenv lock --keep-outdated --requirements > requirements.txt
    && pip install -r requirements.txt

COPY . /code/

CMD ./deploy/scripts/run_prod.sh


FROM server AS celery

RUN apt update -y && apt install -y chromium chromium-driver

CMD ["celery", "-A", "proj", "worker", "-B", "-l", "INFO"]
