from django.core.management.base import BaseCommand

from apps.gidd.publish_check import take_snapshot


class Command(BaseCommand):
    help = "A7.2.6: write the published columns of every GIDD figure to a CSV. Run right after a publish."

    def add_arguments(self, parser):
        parser.add_argument("out_csv")

    def handle(self, *args, **options):
        count = take_snapshot(options["out_csv"])
        self.stdout.write(self.style.SUCCESS(f"Wrote {count} GIDD figures to {options['out_csv']}"))
