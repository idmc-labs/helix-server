import shlex
import subprocess

from django.core.management.base import BaseCommand
from django.utils import autoreload


CMD = (
    "celery -A helix worker -B --concurrency=2 -l INFO "
)


def restart_celery():
    kill_worker_cmd = 'pkill -9 celery'
    subprocess.call(shlex.split(kill_worker_cmd))
    subprocess.call(shlex.split(CMD))


class Command(BaseCommand):

    def handle(self, *args, **options):
        self.stdout.write('Starting celery worker with autoreload...')
        autoreload.run_with_reloader(restart_celery)
