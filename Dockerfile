FROM python:3.8.2-buster AS server

LABEL maintainer="dev@togglecorp.com"

ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN python3 -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /code/

CMD ./deploy/scripts/run_prod.sh


FROM server AS dramatiq

RUN apt update -y && apt install -y chromium chromium-driver

CMD ["python", "manage.py", "rundramatiq"]
