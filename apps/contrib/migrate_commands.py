from django.db.models import Count, Sum

from utils.common import RuntimeProfile
from apps.event.models import Event
from apps.entry.models import Figure
from apps.users.enums import USER_ROLE
from apps.users.utils import HelixInternalBot
from apps.contrib.models import BulkApiOperation
from apps.contrib.bulk_operations.serializers import BulkApiOperationSerializer
from apps.contrib.bulk_operations.tasks import generate_dummy_request


@RuntimeProfile('merge_events')
def merge_events(event_ids_mapping):
    internal_bot = HelixInternalBot()
    api_request = generate_dummy_request(internal_bot.user)

    figure_event_map = {}
    for primary_event_id, other_event_ids in event_ids_mapping.items():
        figures_to_be_updated = Figure.objects.filter(event_id__in=other_event_ids)
        figure_ids = list(figures_to_be_updated.values_list('id', flat=True))
        for figure_id in figure_ids:
            figure_event_map[figure_id] = primary_event_id

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

    event_qs = Event.objects.filter(
        id__in=[
            event_id
            for event_ids in event_ids_mapping.values()
            for event_id in event_ids
        ]
    ).annotate(figure_count=Count('figures'))

    total_processed_events = event_qs.values('id').count()
    total_processed_figures = event_qs.aggregate(total_failed_figure=Sum('figure_count'))['total_failed_figure']

    # Start the bulk operation
    with RuntimeProfile('bulk_operation'):
        with internal_bot.temporary_role(USER_ROLE.ADMIN):
            assert serializer.is_valid() is True, serializer.errors
            serializer.save()

    # Delete event with zero figures
    print('Deleted events:', event_qs.filter(figure_count=0).delete())

    failed_events_count = event_qs.values('id').count()
    failed_figure_count = event_qs.aggregate(total_failed_figure=Sum('figure_count'))['total_failed_figure']
    print(f'Failed to update events: {failed_events_count}/{total_processed_events}')
    print(f'Failed to update figures: {failed_figure_count}/{total_processed_figures}')
