from collections import OrderedDict
from django.db import transaction
from django.utils.translation import gettext
from rest_framework import serializers

from utils.graphene.fields import generate_serializer_field_class
from utils.serializers import GraphqlSupportDrfSerializerJSONField
from apps.event.models import Event
from apps.entry.models import Figure
from apps.extraction.filters import FigureExtractionBulkOperationFilterDataInputType
from apps.contrib.models import BulkApiOperation
from apps.contrib.tasks import run_bulk_api_operation
from apps.contrib.bulk_operations.tasks import get_operation_handler


# ---- Bulk Operation Serializers ----
class BulkApiOperationFilterSerializer(serializers.Serializer):
    figure_role = type(
        'BulkApiOperationFigureRoleFilterSerializer',
        (serializers.Serializer,),
        dict(
            figure=generate_serializer_field_class(
                FigureExtractionBulkOperationFilterDataInputType,
                GraphqlSupportDrfSerializerJSONField,
            )(required=True),
        ),
    )(required=False, allow_null=True)
    figure_event = type(
        'BulkApiOperationFigureEventFilterSerializer',
        (serializers.Serializer,),
        dict(
            figure=generate_serializer_field_class(
                FigureExtractionBulkOperationFilterDataInputType,
                GraphqlSupportDrfSerializerJSONField,
            )(required=True),
        ),
    )(required=False, allow_null=True)


# ---- Payload
class BulkApiOperationFigureRolePayloadSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Figure.ROLE.choices(), required=True)


class BulkApiOperationFigureEventPayloadSerializer(serializers.Serializer):
    by_figures = type(
        'BulkApiOperationFigureEventByFiguresPayloadSerializer',
        (serializers.Serializer,),
        dict(
            figure=serializers.PrimaryKeyRelatedField(queryset=Figure.objects.all(), required=True),
            event=serializers.PrimaryKeyRelatedField(queryset=Event.objects.all(), required=True),
        ),
    )(required=True, many=True)

    def validate(self, attrs):
        by_figures = attrs.get('by_figures') or []

        if not by_figures:
            raise serializers.ValidationError('Please provide data')

        return {
            'by_figures': [
                {
                    # NOTE: Convert Django object to id
                    'figure': by_figure['figure'].pk,
                    'event': by_figure['event'].pk,
                }
                for by_figure in by_figures
            ],
        }


class BulkApiOperationPayloadSerializer(serializers.Serializer):
    figure_role = BulkApiOperationFigureRolePayloadSerializer(required=False, allow_null=True)
    figure_event = BulkApiOperationFigureEventPayloadSerializer(required=False, allow_null=True)


class BulkApiOperationSerializer(serializers.ModelSerializer):
    filters = BulkApiOperationFilterSerializer(required=True)
    payload = BulkApiOperationPayloadSerializer(required=True)

    ACTION_FIELD_MAP = {
        BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_ROLE.value: 'figure_role',
        BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_EVENT.value: 'figure_event',
    }

    class Meta:
        model = BulkApiOperation
        fields = (
            'action',
            'filters',
            'payload',
        )

    def _validate_queryset_count(self, action, filters):
        op_handler = get_operation_handler(action)
        filterset = op_handler.get_filterset()
        _filters = op_handler.get_filters(filters)
        count = filterset(data=_filters).qs.count()

        queryset_count_threshold = self.context.get(
            'QUERYSET_COUNT_THRESHOLD',
            BulkApiOperation.QUERYSET_COUNT_THRESHOLD,
        )
        if count > queryset_count_threshold:
            raise serializers.ValidationError(
                gettext(
                    'Bulk update should include less then %(threshold)s. Current count is %(count)s'
                ) % dict(
                    threshold=queryset_count_threshold,
                    count=count,
                )
            )

    def validate(self, attrs: dict) -> dict:
        op_action = attrs['action']
        op_filters = attrs['filters']
        op_payload = attrs['payload']

        required_field = self.ACTION_FIELD_MAP[op_action]

        # Basic check for fields. Nested Serializer will handle structure
        errors = OrderedDict()
        if required_field not in op_filters:
            errors['filters'] = gettext('Filter not provided')
        if required_field not in op_payload:
            errors['payload'] = gettext('Payload not provided')
        if errors:
            raise serializers.ValidationError(errors)

        self._validate_queryset_count(op_action, op_filters)

        return attrs

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        instance = super().create(validated_data)
        if self.context.get('RUN_TASK_SYNC', False):
            print('Running background task now....')
            run_bulk_api_operation(instance.pk)
        else:
            transaction.on_commit(
                lambda: run_bulk_api_operation.delay(instance.pk)
            )
        return instance

    def update(self, *_):
        raise serializers.ValidationError(gettext('Update not allowed'))
