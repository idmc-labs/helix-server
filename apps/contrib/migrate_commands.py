from unittest.mock import patch

from django.db.models import Count, Sum

from apps.users.models import User
from apps.event.models import Event
from apps.entry.models import Figure
from apps.users.models import Portfolio
from apps.users.enums import USER_ROLE
from apps.contrib.models import BulkApiOperation
from apps.contrib.bulk_operations.serializers import BulkApiOperationSerializer
from apps.contrib.bulk_operations.tasks import generate_dummy_request


def merge_events(data, schema_editor):
    data = {
        '17924': [17925]
    }
    request_user = User.objects.get(email='safar.ligal@togglecorp.com')
    # temp_role, created = Portfolio.objects.get_or_create(
    #     user=request_user,
    #     role=USER_ROLE.ADMIN,
    # )
    api_request = generate_dummy_request(request_user)

    for primary_event_id, other_event_ids in data.items():
        figures_to_be_updated = Figure.objects.filter(event_id__in=other_event_ids)
        figure_ids = list(figures_to_be_updated).values_list('id', flat=True)
        if figure_ids == []:
            return

        figures_snapshot = figures_to_be_updated.values()
        schema_editor.context['updated_figures'].extent(figures_snapshot)

        data = {
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

        serializer = BulkApiOperationSerializer(
            context={
                'request': api_request,
            },
            data=data,
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

        schema_editor.context['deleted_events'].extend(event_qs.filter(figure_count=0).values())
        # Delete event with zero figures
        event_qs.filter(figure_count=0).delete()

        failed_figure_count = event_qs.aggregate(total_failed_figure=Sum('figure_count'))['total_failed_figure']
        print(f'{failed_figure_count} number of Figures failed to update events')
