from unittest.mock import patch

from django.db.models import Count, Sum

from apps.users.models import User
from apps.event.models import Event
from apps.entry.models import Figure
from apps.contrib.models import BulkApiOperation
from apps.contrib.bulk_operations.serializers import BulkApiOperationSerializer
from apps.contrib.bulk_operations.tasks import generate_dummy_request


def merge_events(data):
    api_request = generate_dummy_request(User.objects.get(email='bina.desai@idmc.ch'))

    for primary_event_id, other_event_ids in data.items():
        figure_ids = list(Figure.objects.filter(id__in=other_event_ids).values_list('id', flat=True))

        serializer = BulkApiOperationSerializer(
            context={
                'request': api_request,
            },
            data={
                "action": BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_EVENT.value,
                "filters": {
                    "figure_event": {
                        "figure": {
                            "filter_figure_ids": figure_ids,
                        },
                    }
                },
                "payload": {
                    "figure_event": {
                        "event": primary_event_id,
                    },
                },
            }
        )

        with patch(
            'apps.contrib.bulk_operations.serializers.BulkApiOperation.QUERYSET_COUNT_THRESHOLD',
            len(figure_ids),
        ):
            assert serializer.is_valid() is True, serializer.errors
        with patch(
            'apps.contrib.bulk_operations.serializers.BulkApiOperationSerializer.RUN_TASK_SYNC',
            True,
        ):
            serializer.save()

        event_qs = Event.objects.filter(
            id__in=other_event_ids
        ).annotate(figure_count=Count('figures'))

        # Delete event with zero figures
        event_qs.filter(figure_count=0).delete()

        failed_figure_count = event_qs.aggregate(total_failed_figure=Sum('figure_count'))['total_failed_figure']
        print(f'{failed_figure_count} number of Figures failed to update events')
