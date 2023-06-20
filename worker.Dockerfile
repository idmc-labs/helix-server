FROM python:3.9.16-bullseye

LABEL maintainer="dev@togglecorp.com"

ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN apt update -y && apt install -y chromium chromium-driver

COPY pyproject.toml poetry.lock /code/

# Upgrade pip and install python packages for code
RUN apt-get update -y \
    && apt-get install -y \
        wait-for-it \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade --no-cache-dir pip poetry \
    && poetry --version \
    && pip install setuptools \
    # Configure to use system instead of virtualenvs
    && poetry config virtualenvs.create false \
    && poetry install --no-root \
    # Remove installer
    && pip uninstall -y poetry virtualenv-clone virtualenv

COPY . /code/

CMD ./deploy/scripts/run_tasks.sh
