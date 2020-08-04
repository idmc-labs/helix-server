FROM ubuntu:18.04

MAINTAINER togglecorp info@togglecorp.com

ENV PYTHONUNBUFFERED 1

# Update and install common packages with apt
RUN apt-get update -y && apt-get install -y \
        # Basic Packages
        git \
        locales \
        vim \
        curl \
        gnupg \
        apt-transport-https \
        ca-certificates \
        cron \
        unzip \
        python3 \
        python3-dev \
        python3-setuptools \
        python3-pip \
        # Clean apt
        && rm -rf /var/lib/apt/lists/* \
        && apt-get autoremove

# Support utf-8
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN echo 'alias python=python3\nalias pip=pip3' >> ~/.bashrc \
    && python3 -m pip install --upgrade pip \ 
    && pip3 install -r requirements.txt

COPY . /code/

CMD ["python3", "manage.py", "runserver", "0.0.0.0:9000"]
