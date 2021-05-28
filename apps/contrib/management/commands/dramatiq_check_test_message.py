from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_dramatiq.models import Task


class Command(BaseCommand):
    help = 'Test dramatiq service communication'

    def handle(self, *args, **options):
        self.stdout.write('Checking for message in the last 5 minutes!')
        task = Task.tasks.all().filter(
            status='done',
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).order_by('-created_by').first()
        try:
            assert task is not None
            assert task.actor_name == 'dramatiq_says_hello'
            self.stdout.write(self.style.SUCCESS('Message received!'))
        except AssertionError:
            self.stdout.write(self.style.ERROR('Message not found!'))
