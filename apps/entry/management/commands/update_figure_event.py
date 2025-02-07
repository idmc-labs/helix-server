import csv

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.entry.models import Figure
from apps.event.models import Event
from apps.users.enums import USER_ROLE
from apps.contrib.models import BulkApiOperation
from apps.contrib.bulk_operations.serializers import BulkApiOperationSerializer
from apps.contrib.bulk_operations.tasks import generate_dummy_request
from apps.users.utils import HelixInternalBot
from utils.common import RuntimeProfile


class Command(BaseCommand):
    help = "Update figure event with the new event"

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        figures_file = kwargs['csv_file_path']

        figure_event_map = {}
        event_ids = set()
        new_event_ids = set()

        with open(figures_file, 'r') as file:
            reader = csv.DictReader(file)
            next(reader)  # Skip headers

            for row in reader:
                figure_id = int(row['ID'])
                event_id = int(row['Event ID'])
                new_event_id = int(row['New Event ID'])
                if row['Event to be deleted']:
                    event_ids.add(int(row['Event to be deleted']))

                figure_instance = Figure.objects.filter(id=figure_id).first()
                if not figure_instance:
                    self.stdout.write(self.style.ERROR(f'Figure with ID {figure_id} not found'))
                    continue

                if figure_instance.event_id != event_id:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Expected event ID {event_id} for figure ID {figure_id}, but found {figure_instance.event_id}'
                        )
                    )
                    continue

                if not Event.objects.filter(id=new_event_id).first():
                    new_event_ids.add(new_event_id)
                    continue

                figure_event_map[figure_id] = new_event_id

        # Helix Bot
        internal_bot = HelixInternalBot()
        api_request = generate_dummy_request(internal_bot.user)

        data = {
            "action": BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_EVENT.value,
            "filters": {
                "figure_event": {
                    "figure": {
                        "filter_figure_ids": list(figure_event_map.keys()),
                    },
                }
            },
            "payload": {
                "figure_event": {
                    "by_figures": [
                        {
                            "figure": figure_id,
                            "event": event_id,
                        }
                        for figure_id, event_id in figure_event_map.items()
                    ],
                },
            },
        }

        serializer = BulkApiOperationSerializer(
            context={
                'request': api_request,
                'QUERYSET_COUNT_THRESHOLD': len(figure_event_map),
                'RUN_TASK_SYNC': True,
            },
            data=data,
        )

        # Start the bulk operation
        with RuntimeProfile('bulk_operation'):
            with internal_bot.temporary_role(USER_ROLE.ADMIN):
                assert serializer.is_valid() is True, serializer.errors
                serializer.save()

        event_figure_qs = Event.objects.filter(id__in=list(event_ids)).annotate(
            total_figure_count=Count('figures')
        )

        if new_event_ids:
            self.stdout.write(
                self.style.ERROR(
                    f'New Events not found: {new_event_ids}'
                )
            )

        # Delete the events that arenot associated with any figures
        self.stdout.write(
            self.style.SUCCESS(
                f'Deleted events: {event_figure_qs.filter(total_figure_count=0).delete()}'
            )
        )

        # Events associated with figure will not be deleted
        self.stdout.write(
            self.style.ERROR(
                f'Failed to delete events: {event_figure_qs.filter(total_figure_count__gt=0).values_list("id", flat=True)}'
            )
        )
