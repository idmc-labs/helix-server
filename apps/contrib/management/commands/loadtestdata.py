from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string


class Command(BaseCommand):
    help = 'Create dummy instances.'

    def add_arguments(self, parser):
        parser.add_argument('models', nargs='+', type=str)
        parser.add_argument('--count', nargs='?', const=1, default=1, type=int)

    def handle(self, *args, **options):
        for model in options['models']:
            factory = import_string(f'utils.factories.{model}Factory')
            factory.create_batch(options['count'])
