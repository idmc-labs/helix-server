from django.core.management.base import BaseCommand

from apps.contact.models import (
    CommunicationMedium,
)


MEDIA = ['Email', 'Skype', 'SMS']


class Command(BaseCommand):
    help = 'Initialize communication media.'

    def handle(self, *args, **options):
        for medium in MEDIA:
            CommunicationMedium.objects.get_or_create(name=medium.lower())
        self.stdout.write(self.style.SUCCESS(
            'Saved {} communication media.'.format(
                CommunicationMedium.objects.count(),
            )
        ))

