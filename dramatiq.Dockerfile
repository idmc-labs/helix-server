FROM python:3.8.2-buster

LABEL maintainer="dev@togglecorp.com"

ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN apt update -y && apt install -y chromium chromium-driver

COPY ./requirements.txt /code/requirements.txt
RUN python3 -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /code/

CMD ["python", "manage.py", "rundramatiq", "--reload"]
