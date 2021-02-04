#! /bin/bash

# FIXME: couldn't directly call dramatiq because of generated arguments
python3 manage.py rundramatiq &

uwsgi --ini /code/deploy/configs/uwsgi.ini # Start uwsgi server
