from django.core.management.base import BaseCommand

from apps.contrib.tasks import dramatiq_says_hello


class Command(BaseCommand):
    help = 'Test dramatiq service communication'

    def handle(self, *args, **options):
        print('Sending a message...')
        dramatiq_says_hello.send('dramatiq')
        print('Message sent! In the dramamtiq service run:\n\npython manage.py dramatiq_check_test_message\n')
