from django.core.management.base import BaseCommand, CommandError

from apps.gidd.publish_check import compare_snapshots


class Command(BaseCommand):
    help = (
        "A7.2.6: compare two snapshot_gidd_figures CSVs taken on the same data before and after A7.2.3. "
        "PASS only if the rows match, only sources_type changes and sources_sub_type is the only new column. "
        "Writes report.md and changed_cells.csv to <out_dir>."
    )

    def add_arguments(self, parser):
        parser.add_argument("before_csv")
        parser.add_argument("after_csv")
        parser.add_argument("out_dir")

    def handle(self, *args, **options):
        passed, failures = compare_snapshots(options["before_csv"], options["after_csv"], options["out_dir"])
        report = f"{options['out_dir']}/report.md"
        if not passed:
            raise CommandError(f"FAIL: {'; '.join(failures)}. See {report}")
        self.stdout.write(self.style.SUCCESS(f"PASS. See {report}"))
