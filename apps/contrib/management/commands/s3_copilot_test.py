from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage


class Command(BaseCommand):
    help = 'Test copilot service for s3 access'

    def handle(self, *args, **options):
        default_storage.exists('storage_test')
        print('Reading objects list passed!')
        file = default_storage.open('storage_test', 'w')
        file.close()
        file = default_storage.open('storage_test', 'w')
        file.write('storage contents')
        file.close()
        print('Writing passed!')
        file = default_storage.open('storage_test', 'r')
        file.read()
        file.close()
        print('Reading object passed!')
        default_storage.delete('storage_test')
        print('Deleting object passed!')
