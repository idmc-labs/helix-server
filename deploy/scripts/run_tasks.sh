#! /bin/bash

# https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html#starting-the-scheduler
echo "Running Scheduler"
celery -A helix beat -l INFO -s ~/celerybeat-schedule &

echo "Running Task Runner"
celery -A helix worker -l INFO --concurrency=4
# https://hackernoon.com/using-celery-with-multiple-queues-retries-and-scheduled-tasks-589fe9a4f9ba
# celery -A helix worker -l INFO --concurrency=4 -Q celery_low &
# celery -A helix worker -l INFO --concurrency=2 -Q celery_high
# This wont even run
