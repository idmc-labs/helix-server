FROM python:3.8.2-buster

MAINTAINER togglecorp info@togglecorp.com

ENV PYTHONUNBUFFERED 1

RUN apt-get update -y && \
    apt-get install -y wkhtmltopdf

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install -r requirements.txt

COPY . /code/

CMD ["python", "manage.py", "runserver", "0.0.0.0:9000"]
