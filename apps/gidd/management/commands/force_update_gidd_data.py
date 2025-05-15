from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.gidd.models import StatusLog
from apps.gidd.tasks import update_gidd_data
from apps.users.utils import HelixInternalBot


class Command(BaseCommand):
    """
    Management command to force update GIDD data.
    """

    help = "Force update GIDD data"

    def handle(self, *args, **kwargs):
        """
        Executes the command to force update GIDD data.
        """
        if not settings.DEBUG:
            self.stderr.write("This command is only intended for local development.")

        internal_bot = HelixInternalBot()
        status_log = StatusLog.objects.create(
            triggered_by=internal_bot.user,
            triggered_at=timezone.now(),
        )
        update_gidd_data(status_log.pk)
