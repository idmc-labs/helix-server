import os

from banjo_utils.celery_health.worker import setup_worker_heartbeat
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "helix.settings")

app = Celery("helix")
setup_worker_heartbeat(app)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")


def _every_minutes(minutes):
    """Beat entry fields for a task that runs every ``minutes``.

    The queued message expires after one full period, so a run that is still
    waiting when its replacement is published is discarded rather than running
    back to back with it. At most one run of the task is ever pending.

    NOTE: the option is `expire_seconds`, not celery's usual `expires`.
    django_celery_beat's DatabaseScheduler reads only the former and drops the
    latter on the way into the database.
    """
    return {
        "schedule": crontab(minute=f"*/{minutes}"),
        "options": {"expire_seconds": minutes * 60},
    }


def _every_hours(hours, minute="0"):
    """Beat entry fields for a task that runs every ``hours``. See `_every_minutes`."""
    return {
        "schedule": crontab(minute=minute, hour=f"*/{hours}"),
        "options": {"expire_seconds": hours * 60 * 60},
    }


app.conf.beat_schedule = {
    "kill-exports": {
        "task": "apps.contrib.tasks.kill_all_old_excel_exports",
        "args": [],
        **_every_minutes(15),
    },
    "kill-stale-gidd-generations": {
        "task": "apps.gidd.tasks.kill_all_stale_gidd_generations",
        "args": [],
        **_every_minutes(15),
    },
    "kill-previews": {
        "task": "apps.contrib.tasks.kill_all_long_running_previews",
        "args": [],
        **_every_hours(2),
    },
    "kill-report-generations": {
        "task": "apps.contrib.tasks.kill_all_long_running_report_generations",
        "args": [],
        **_every_hours(3),
    },
    # NOTE: when we change the schedule, we should also update the metadata
    # for the external APIs
    "generate-idus-dump-file": {
        "task": "apps.contrib.tasks.generate_idus_dump_file",
        "args": [],
        **_every_hours(2),
    },
    "generate-idus-all-dump-file": {
        "task": "apps.contrib.tasks.generate_idus_all_dump_file",
        "args": [],
        **_every_hours(2),
    },
    "generate-idus-all-disaster-dump-file": {
        "task": "apps.contrib.tasks.generate_idus_all_disaster_dump_file",
        "args": [],
        **_every_hours(2),
    },
    "generate-idu-options-dump-file": {
        "task": "apps.contrib.tasks.generate_idu_options_dump_file",
        "args": [],
        **_every_hours(2),
    },
    "save_and_delete_tracked_data_from_redis_to_db": {
        "task": "apps.contrib.tasks.save_and_delete_tracked_data_from_redis_to_db",
        "args": [],
        **_every_hours(24, minute="1"),
    },
    # Backstop that frees the single-import lock when a worker dies mid-import
    # and leaves a row stuck at IN_PROGRESS.
    "fail-stale-hulk-bulk-imports": {
        "task": "apps.hulk.tasks.fail_stale_hulk_bulk_imports",
        "args": [],
        **_every_minutes(15),
    },
}

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
