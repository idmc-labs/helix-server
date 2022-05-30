from django.core.management.base import BaseCommand
from apps.event.models import OtherSubType


class Command(BaseCommand):
    help = 'Initialize or update other sub type.'

    def handle(self, *args, **options):
        other_sub_type_list = [
            'Development', 'Eviction', 'Technical disaster'
        ]
        for name in other_sub_type_list:
            if not OtherSubType.objects.filter(name__iexact=name).exists():
                OtherSubType.objects.create(name=name)
        self.stdout.write(self.style.SUCCESS('Saved {} other subtypes.'.format(
            OtherSubType.objects.count(),
        )))
