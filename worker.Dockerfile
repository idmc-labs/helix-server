FROM python:3.8.16-bullseye

LABEL maintainer="dev@togglecorp.com"

ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN apt update -y && apt install -y chromium chromium-driver

COPY pyproject.toml poetry.lock /code/

# Upgrade pip and install python packages for code
RUN pip install --upgrade --no-cache-dir pip poetry \
    && poetry --version \
    # Configure to use system instead of virtualenvs
    && poetry config virtualenvs.create false \
    && poetry install --no-root \
    # Remove installer
    && pip uninstall -y poetry virtualenv-clone virtualenv

COPY . /code/

CMD ./deploy/scripts/run_tasks.sh
