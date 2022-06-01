from django.core.management.base import BaseCommand
from apps.event.models import ContextOfViolence


class Command(BaseCommand):
    help = 'Initialize or update other context of violences'

    def handle(self, *args, **options):
        other_sub_type_list = [
            'Ethnic tensions',
            'Religious tensions',
            'Agricultural/Pastoralist tensions',
            'Host/Displaced tensions',
            'Elections',
            'Demonstrations',
            'Police operations',
            'Banditry',
            'Disputes between criminal groups',
            'Clashes between criminal actors and State actors',
            'Other',
        ]
        for name in other_sub_type_list:
            if not ContextOfViolence.objects.filter(name__iexact=name).exists():
                ContextOfViolence.objects.create(name=name)
        self.stdout.write(self.style.SUCCESS('Saved {} context of violences.'.format(
            ContextOfViolence.objects.count(),
        )))
