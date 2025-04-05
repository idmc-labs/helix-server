import os

from celery import Celery, signals
from celery.schedules import crontab
from utils.celery import LivenessProbe
from logging.config import dictConfig


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helix.settings')

app = Celery('helix')
app.steps["worker"].add(LivenessProbe)  # type: ignore[reportOptionalSubscript]

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

    # NOTE: when we change the schedule, we should also update the metadata
    # for the external APIs
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

@signals.setup_logging.connect
def config_loggers(**_):
    from django.conf import settings
 
    dictConfig(settings.LOGGING)



@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
