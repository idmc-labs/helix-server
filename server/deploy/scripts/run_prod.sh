#! /bin/bash

# TODO: Only run this once per migration
python3 manage.py migrate

uwsgi --ini /code/deploy/configs/uwsgi.ini # Start uwsgi server
