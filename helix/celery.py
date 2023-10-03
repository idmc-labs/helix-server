import os

from celery import Celery
from celery.schedules import crontab


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helix.settings')

app = Celery('helix')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    'kill-exports': {
        'task': 'apps.contrib.tasks.kill_all_old_excel_exports',
        'schedule': crontab(minute='*/15'),
        'args': [],
    },
    'kill-previews': {
        'task': 'apps.contrib.tasks.kill_all_long_running_previews',
        'schedule': crontab(minute='0', hour='*/2'),
        'args': [],
    },
    'kill-report-generations': {
        'task': 'apps.contrib.tasks.kill_all_long_running_report_generations',
        'schedule': crontab(minute='0', hour='*/3'),
        'args': [],
    },

    'generate-idus-dump-file': {
        'task': 'apps.contrib.tasks.generate_idus_dump_file',
        'schedule': crontab(minute='0', hour='*/2'),
        'args': [],
    },
    'generate-idus-all-dump-file': {
        'task': 'apps.contrib.tasks.generate_idus_all_dump_file',
        'schedule': crontab(minute='0', hour='*/2'),
        'args': [],
    },
    'generate-idus-all-disaster-dump-file': {
        'task': 'apps.contrib.tasks.generate_idus_all_disaster_dump_file',
        'schedule': crontab(minute='0', hour='*/2'),
        'args': [],
    },

    'save_and_delete_tracked_data_from_redis_to_db': {
        'task': 'apps.contrib.tasks.save_and_delete_tracked_data_from_redis_to_db',
        'schedule': crontab(minute='1', hour='*/24'),
        'args': [],
    },
}

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
