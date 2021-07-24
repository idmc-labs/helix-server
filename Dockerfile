FROM python:3.8.2-buster AS server

LABEL maintainer="dev@togglecorp.com"

ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY Pipfile Pipfile.lock /code
RUN pip install --upgrade --no-cache-dir pip pipenv \
    && pipenv install --dev --system --deploy \
    && pip uninstall -y pipenv virtualenv-clone virtualenv

COPY . /code/

CMD ./deploy/scripts/run_prod.sh


FROM server AS celery

RUN apt update -y && apt install -y chromium chromium-driver

CMD ["celery", "-A", "proj", "worker", "-B", "-l", "INFO"]
