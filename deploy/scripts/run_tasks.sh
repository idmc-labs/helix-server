#! /bin/bash

# https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html#starting-the-scheduler
echo "Running Scheduler"
celery -A helix beat -l INFO -s ~/celerybeat-schedule &

echo "Running Task Runner"
celery -A helix worker -l INFO
