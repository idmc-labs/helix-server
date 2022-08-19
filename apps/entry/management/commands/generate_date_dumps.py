import json
import re
import datetime
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.helixmigration.models import (
    Facts,
    ContextualAnalysis,
    Documents,
    Events,
    Communications,
)


class Command(BaseCommand):
    '''
    This command requires old database connection, which is currently
    in feature/find_bugs branch
    '''
    help = 'Generate dates dump'

    def parse_date(self, date_field):
        try:
            return datetime.datetime.strptime(date_field, "%Y-%m-%d").date() if date_field else None
        except ValueError:
            # Don't handle timezone
            return re.split("T", date_field)[0] if date_field else None

    def handle(self, *args, **options):
        # Dump figure dates
        facts = Facts.objects.using('helixmigration').filter(
            Q(start_date__has_key='date') |
            Q(end_date__has_key='date')
        ).values('id', 'start_date', 'end_date')
        facts_data = {
            item['id']: {
                'start_date': self.parse_date(item.get('start_date').get('date')) if item.get('start_date') else None,
                'end_date': self.parse_date(item['end_date'].get('date')) if item.get('end_date') else None
            } for item in facts
        }
        out_file = open("figure_dates.json", "w")
        json.dump(
            facts_data,
            out_file,
            indent=6,
            ensure_ascii=False,
            default=str
        )
        out_file.close()

        # Dump entry dates
        documents = Documents.objects.using('helixmigration').filter(
            publication_date__isnull=False
        ).values('id', 'publication_date')
        documents_data = {item['id']: item['publication_date'] for item in documents}
        out_file = open("entry_dates.json", "w")
        json.dump(
            documents_data,
            out_file,
            indent=6,
            ensure_ascii=False,
            default=str
        )
        out_file.close()

        # Dump event dates
        events = Events.objects.using('helixmigration').filter(
            Q(start_date__has_key='date') |
            Q(end_date__has_key='date')
        ).values('id', 'start_date', 'end_date')
        event_data = {
            item['id']: {

                'start_date': self.parse_date(item.get('start_date').get('date')) if item.get('start_date') else None,
                'end_date': self.parse_date(item['end_date'].get('date')) if item.get('end_date') else None
            } for item in events
        }
        out_file = open("event_dates.json", "w")
        json.dump(
            event_data,
            out_file,
            indent=6,
            ensure_ascii=False,
            default=str
        )
        out_file.close()

        # Dump contextual analysis dates
        contextual_analysis = ContextualAnalysis.objects.using('helixmigration').filter(
            publication_date__isnull=False
        ).values('id', 'publication_date')
        contextual_analysis_data = {item['id']: item['publication_date'] for item in contextual_analysis}
        out_file = open("contextual_analysis_dates.json", "w")
        json.dump(
            contextual_analysis_data,
            out_file,
            indent=6,
            ensure_ascii=False,
            default=str
        )
        out_file.close()

        # Dump contacts dates
        communications = Communications.objects.using('helixmigration').filter(
            conducted_at__isnull=False
        ).values('id', 'conducted_at')
        communications_data = {item['id']: item.get('conducted_at') for item in communications}
        out_file = open("communication_dates.json", "w")
        json.dump(
            communications_data,
            out_file,
            indent=6,
            ensure_ascii=False,
            default=str
        )
        out_file.close()
