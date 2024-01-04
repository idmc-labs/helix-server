from django.db import transaction
from django.utils.translation import gettext
from rest_framework import serializers

from utils.graphene.fields import generate_serializer_field_class
from utils.serializers import GraphqlSupportDrfSerializerJSONField
from apps.entry.models import Figure
from apps.extraction.filters import FigureExtractionFilterDataInputType
from apps.contrib.models import BulkApiOperation
from apps.contrib.tasks import run_bulk_api_operation


# ---- Bulk Operation Serializers ----
class BulkApiOperationFilterSerializer(serializers.Serializer):
    figure_role = type(
        'BulkApiOperationFigureRoleFilterSerializer',
        (serializers.Serializer,),
        dict(
            figure=generate_serializer_field_class(
                FigureExtractionFilterDataInputType,
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


class BulkApiOperationSerializer(serializers.ModelSerializer):
    filters = BulkApiOperationFilterSerializer(required=True)
    payload = BulkApiOperationPayloadSerializer(required=True)

    ACTION_FIELD_MAP = {
        BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_ROLE.value: 'figure_role',
    }

    class Meta:
        model = BulkApiOperation
        fields = (
            'action',
            'filters',
            'payload',
        )

    def validate(self, attrs: dict) -> dict:
        op_action = attrs['action']
        op_filters = attrs['filters']
        op_payload = attrs['payload']

        required_field = self.ACTION_FIELD_MAP[op_action]

        # Basic check for fields. Nested Serializer will handle structure
        if required_field not in op_filters:
            raise serializers.ValidationError(gettext('Filter not provided'))
        if required_field not in op_payload:
            raise serializers.ValidationError(gettext('Payload not provided'))

        # TODO: Add queryset with filter count to not be greater then specified threshold
        return attrs

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        instance = super().create(validated_data)
        transaction.on_commit(
            lambda: run_bulk_api_operation.delay(instance.pk)
        )
        return instance

    def update(self, *_):
        raise serializers.ValidationError(gettext('Update not allowed'))
