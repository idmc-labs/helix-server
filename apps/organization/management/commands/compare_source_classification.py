from django.core.management.base import BaseCommand, CommandError

from apps.organization.source_classification_snapshot import compare_snapshots


class Command(BaseCommand):
    help = (
        "Compare two snapshot_source_classification directories and write report.md, "
        "organizations_moved.csv and figures_changed.csv to <out_dir>. Fails if an organization "
        "is missing after, or lost its kind."
    )

    def add_arguments(self, parser):
        parser.add_argument("before_dir")
        parser.add_argument("after_dir")
        parser.add_argument("out_dir")

    def handle(self, *args, **options):
        counts = compare_snapshots(options["before_dir"], options["after_dir"], options["out_dir"])
        summary = ", ".join(f"{key}: {value}" for key, value in counts.items())
        if counts["problems"]:
            raise CommandError(f"{summary}. See {options['out_dir']}/report.md")
        self.stdout.write(self.style.SUCCESS(f"{summary}. Report: {options['out_dir']}/report.md"))
