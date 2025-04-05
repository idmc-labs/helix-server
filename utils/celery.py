# https://github.com/celery/celery/issues/4079#issuecomment-1128954283
import logging
from pathlib import Path

from celery import bootsteps
from celery.signals import beat_init, worker_ready, worker_shutdown  # type: ignore[worker]

WORKER_HEARTBEAT_FILE = Path("/tmp/worker_heartbeat")
WORKER_READINESS_FILE = Path("/tmp/worker_ready")

WORKER_BEAT_READINESS_FILE = Path("/tmp/worker_beat_ready")

logger = logging.getLogger(__name__)


def touch_file(path: Path):
    logger.debug('Touch %s', path)
    path.touch()


def unlink_file(path: Path):
    logger.debug('Unlink %s', path)
    path.unlink(missing_ok=True)


class LivenessProbe(bootsteps.StartStopStep):
    requires = {"celery.worker.components:Timer"}

    def __init__(self, parent, **kwargs):
        self.requests = []
        self.tref = None

    def start(self, parent):
        touch_file(WORKER_HEARTBEAT_FILE)
        self.tref = parent.timer.call_repeatedly(
            60,
            self.update_heartbeat_file,
            (parent,),
            priority=10,
        )

    def stop(self, parent):
        unlink_file(WORKER_HEARTBEAT_FILE)

    def update_heartbeat_file(self, parent):
        touch_file(WORKER_HEARTBEAT_FILE)


@worker_ready.connect  # type: ignore[worker]
def worker_ready(**_):
    touch_file(WORKER_READINESS_FILE)


@worker_shutdown.connect  # type: ignore[worker]
def worker_shutdown(**_):
    unlink_file(WORKER_READINESS_FILE)


@beat_init.connect
def beat_ready(**_):
    touch_file(WORKER_BEAT_READINESS_FILE)
