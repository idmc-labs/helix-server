FROM python:3.8.5-buster

MAINTAINER togglecorp info@togglecorp.com

ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install -r requirements.txt

COPY . /code/

RUN python manage.py migrate \
    && python manage.py loaddata fixtures/users.json \
    && python manage.py collectstatic --noinput \
    && python manage.py graphql_schema
CMD ["python", "manage.py", "runserver", "0.0.0.0:9000"]
