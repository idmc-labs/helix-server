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


class BulkApiOperationPayloadSerializer(serializers.Serializer):
    figure_role = type(
        'BulkApiOperationFigureRolePayloadSerializer',
        (serializers.Serializer,),
        dict(
            role=serializers.ChoiceField(choices=Figure.ROLE.choices()),
        ),
    )(required=False, allow_null=True)
    figure_event = type(
        'BulkApiOperationFigureEventPayloadSerializer',
        (serializers.Serializer,),
        dict(
            event=serializers.PrimaryKeyRelatedField(queryset=Event.objects.all()),
        ),
    )(required=False, allow_null=True)

    def validate_figure_event(self, v):
        # NOTE: Convert Event object to id
        return {
            'event': v['event'].id
        }


class BulkApiOperationSerializer(serializers.ModelSerializer):
    filters = BulkApiOperationFilterSerializer(required=True)
    payload = BulkApiOperationPayloadSerializer(required=True)

    ACTION_FIELD_MAP = {
        BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_ROLE.value: 'figure_role',
        BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_EVENT.value: 'figure_event',
    }
    RUN_TASK_SYNC = False

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

        if count > BulkApiOperation.QUERYSET_COUNT_THRESHOLD:
            raise serializers.ValidationError(
                gettext(
                    'Bulk update should include less then %(threshold)s. Current count is %(count)s'
                ) % dict(
                    threshold=BulkApiOperation.QUERYSET_COUNT_THRESHOLD,
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
        if self.RUN_TASK_SYNC:
            print('Running background task now....')
            run_bulk_api_operation(instance.pk)
        else:
            transaction.on_commit(
                lambda: run_bulk_api_operation.delay(instance.pk)
            )
        return instance

    def update(self, *_):
        raise serializers.ValidationError(gettext('Update not allowed'))
