import json

from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.helixmigration.models import Facts


class Command(BaseCommand):
    """
    This command requires old database connection, which is currently
    in feature/find_bugs branch
    """

    help = "Migrate sources and reliability."

    def handle(self, *args, **options):
        fact = Facts.objects.using("helixmigration").annotate(
            sources_and_reliability=KeyTextTransform("souces", "data"),
        )
        out_file = open("sources_and_reliability.json", "w")
        json.dump(
            list(fact.filter(~Q(sources_and_reliability__in=[None, ""])).values("id", "sources_and_reliability")),
            out_file,
            indent=6,
        )
        out_file.close()
