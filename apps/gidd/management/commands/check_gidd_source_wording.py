from django.core.management.base import BaseCommand, CommandError

from apps.gidd.publish_check import check_source_wording


class Command(BaseCommand):
    help = (
        "Check a snapshot_gidd_figures CSV of a release published after data migration: every sources_type "
        "is a source type name, every sources_sub_type a subtype name, and the lists line up."
    )

    def add_arguments(self, parser):
        parser.add_argument("snapshot_csv")

    def handle(self, *args, **options):
        problems = check_source_wording(options["snapshot_csv"])
        if problems:
            raise CommandError("FAIL:\n- " + "\n- ".join(problems))
        self.stdout.write(self.style.SUCCESS("PASS"))
