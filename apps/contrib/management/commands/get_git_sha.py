import subprocess

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Get latest git SHA'

    def handle(self, *args, **options):
        return subprocess.check_output(['git', 'describe', '--always']).strip()
