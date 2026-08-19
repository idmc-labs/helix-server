from banjo_utils.celery_health.database import HeartbeatDatabaseScheduler
from django_celery_beat.models import PeriodicTask


class HelixDatabaseScheduler(HeartbeatDatabaseScheduler):
    """Database scheduler seeded from ``app.conf.beat_schedule``.

    ``beat_schedule`` is the source of truth for which tasks exist and how they
    are scheduled. Every beat start rewrites each ``PeriodicTask`` from it and
    drops rows whose entry is gone. ``enabled`` is the one field the rewrite
    leaves alone, so a task switched off in the admin panel stays off; beat
    picks the change up within ``max_interval``, without a restart.
    """

    def __init__(self, *args, **kwargs):
        self._synced_names = set()
        super().__init__(*args, **kwargs)

    def setup_schedule(self):
        self._synced_names.clear()
        super().setup_schedule()
        PeriodicTask.objects.exclude(name__in=self._synced_names).delete()

    def update_from_dict(self, mapping):
        # setup_schedule() feeds this both beat_schedule and celery's built-in
        # entries; together they are the full set of names beat owns.
        self._synced_names.update(mapping)
        super().update_from_dict(mapping)
