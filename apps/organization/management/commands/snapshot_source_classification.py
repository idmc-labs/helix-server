from django.core.management.base import BaseCommand

from apps.organization.source_classification_snapshot import take_snapshot


class Command(BaseCommand):
    help = (
        "Write each organization's kind and each figure's classification and IDU source wording "
        "to <out_dir>/organizations.csv and <out_dir>/figures.csv."
    )

    def add_arguments(self, parser):
        parser.add_argument("out_dir")

    def handle(self, *args, **options):
        counts = take_snapshot(options["out_dir"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {counts['organizations']} organizations and {counts['figures']} figures to {options['out_dir']}"
            )
        )
