from django.core.management.base import BaseCommand

from apps.event.constants import OSV_SUB_TYPE
from apps.event.models import OsvSubType


class Command(BaseCommand):
    help = 'Initialize or update event osv sub types.'

    def handle(self, *args, **options):
        for name in OSV_SUB_TYPE:
            if not OsvSubType.objects.filter(name__iexact=name).exists():
                OsvSubType.objects.create(name=name)
        self.stdout.write(self.style.SUCCESS('Saved {} osv subtypes.'.format(
            OsvSubType.objects.count(),
        )))
