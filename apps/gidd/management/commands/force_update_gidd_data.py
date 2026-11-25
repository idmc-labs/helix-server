from django.core.management.base import BaseCommand, CommandError

from apps.gidd.models import StatusLog
from apps.gidd.tasks import GiddRunRefused, start_gidd_update_run
from apps.users.utils import HelixInternalBot


class Command(BaseCommand):
    help = "Force update GIDD data for a release"

    def add_arguments(self, parser):
        parser.add_argument("--release-id", type=int, required=True, help="ID of the GIDD release to publish")

    def handle(self, *args, **options):
        internal_bot = HelixInternalBot()

        try:
            status_log = start_gidd_update_run(
                release_id=options["release_id"],
                user=internal_bot.user,
                run_async=False,
            )
        except GiddRunRefused as e:
            raise CommandError(str(e))

        status_log.refresh_from_db()
        status = StatusLog.Status.get(status_log.status).label

        self.stdout.write(f"GIDD run {status_log.pk} finished with status {status}.")
