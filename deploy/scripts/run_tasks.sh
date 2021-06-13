#! /bin/bash

# Keeping with dramatiq because it is a really small scheduling service
echo "Running Scheduler"
python manage.py runapscheduler &

echo "Running Dramatiq"
python manage.py rundramatiq --reload
