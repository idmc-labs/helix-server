import requests
from django.core.management.base import BaseCommand
from apps.entry.models import Figure, Entry
from apps.event.models import Event
from apps.contextualupdate.models import ContextualUpdate
from apps.contact.models import Communication


class Command(BaseCommand):
    help = 'Update date fields'

    def handle(self, *args, **options):
        ########################################
        # Update figure dates
        ########################################

        figure_data = requests.get(
            'https://helix-copilot-staging-helix-media.s3.amazonaws.com/media/figure_dates.json'
        ).json()
        figures = Figure.objects.filter(old_id__in=figure_data.keys())
        for figure in figures:
            figure_date = figure_data.get(figure.old_id)
            figure.start_date = figure_date['start_date']
            figure.end_date = figure_date['end_date']
        Figure.objects.bulk_update(figures, ['start_date', 'end_date'])
        print(f'{figures.count()} figures updated')

        ########################################
        # Update event dates
        ########################################
        event_data = requests.get(
            'https://helix-copilot-staging-helix-media.s3.amazonaws.com/media/event_dates.json'
        ).json()
        events = Event.objects.filter(old_id__in=event_data.keys())
        for event in events:
            event_date = event_data.get(event.old_id)
            if event_date['start_date'] and event_date['end_date']:
                event.start_date = event_date['start_date']
                event.end_date = event_date['end_date']
        Event.objects.bulk_update(events, ['start_date', 'end_date'])
        print(f'{events.count()} events updated')

        #########################################
        # Update entry dates
        #########################################
        entry_data = requests.get(
            'https://helix-copilot-staging-helix-media.s3.amazonaws.com/media/entry_dates.json'
        ).json()
        entries = Entry.objects.filter(old_id__in=entry_data.keys())
        for entry in entries:
            entry.publish_date = entry_data.get(entry.old_id)
        print(f'{entries.count()} entries updated')

        #########################################
        # Update contextual update dates
        #########################################
        contextual_update_data = requests.get(
            'https://helix-copilot-staging-helix-media.s3.amazonaws.com/media/contextual_analysis_dates.json'
        ).json()
        contextual_updates = ContextualUpdate.objects.filter(old_id__in=contextual_update_data.keys())
        for contextual_update in contextual_updates:
            contextual_update.publish_date = contextual_update_data.get(contextual_update.old_id)
        print(f'{contextual_updates.count()} contextual updates updated')

        #########################################
        # Update communication dates
        #########################################
        communication_data = requests.get(
            'https://helix-copilot-staging-helix-media.s3.amazonaws.com/media/communication_dates.json'
        ).json()
        communications = Communication.objects.filter(old_id__in=communication_data.keys())
        for communication in communications:
            communication.date = communication_data.get(communication.old_id)
        print(f'{communications.count()} communications updated')
