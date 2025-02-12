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
        parser.add_argument(
            '--delete-empty-events',
            action='store_true',
            help='Delete events that are not associated with any figures'
        )

    def update_figure_event(self, figure_event_map: dict) -> None:
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
                            "event": new_event_id,
                        }
                        for figure_id, new_event_id in figure_event_map.items()
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

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file_path']

        figure_event_map = {}
        events_id_to_be_deleted = set()

        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)

            for row in reader:
                figure_id = int(row['ID'])
                event_id = int(row['Event ID'])
                new_event_id = int(row['New Event ID'])
                events_id_to_be_deleted.add(event_id)

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
                    self.stdout.write(
                        self.style.ERROR(
                            f'Expected new event ID {new_event_id} for figure ID {figure_id} has not been found'
                        )
                    )
                    continue

                figure_event_map[figure_id] = new_event_id

        if figure_event_map:
            self.update_figure_event(figure_event_map)
        else:
            self.stdout.write(
                self.style.ERROR(
                    'No figure event to be updated'
                )
            )

        if kwargs['delete_empty_events']:
            event_to_be_deleted_qs = Event.objects.filter(id__in=list(events_id_to_be_deleted)).annotate(
                total_figure_count=Count('figures')
            )

            # Delete the events that arenot associated with any figures
            events_to_be_deleted_stat = event_to_be_deleted_qs.filter(total_figure_count=0).delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Deleted events: {events_to_be_deleted_stat}'
                )
            )

            # Events associated with figure will not be deleted
            failed_to_delete_event_stat = event_to_be_deleted_qs.filter(
                total_figure_count__gt=0
            ).values_list("id", flat=True)
            self.stdout.write(
                self.style.ERROR(
                    f'Failed to delete events: {failed_to_delete_event_stat}'
                )
            )
