import magic
from datetime import timedelta
from django.utils import timezone

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext
from django.db import transaction
from rest_framework import serializers

from utils.graphene.fields import generate_serializer_field_class
from utils.serializers import GraphqlSupportDrfSerializerJSONField, IntegerIDField
from apps.entry.models import Figure
from apps.entry.tasks import PDF_TASK_TIMEOUT
from apps.extraction.filters import FigureExtractionFilterDataInputType
from apps.contrib.tasks import run_bulk_api_operation
from apps.contrib.models import (
    Attachment,
    BulkApiOperation,
    Client,
    ExcelDownload,
    SourcePreview,
)


class MetaInformationSerializerMixin(serializers.Serializer):
    """
    Responsible to add following fields into the validated data
    - created_by
    - last_modified_by
    """
    created_at = serializers.DateTimeField(read_only=True)
    modified_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    last_modified_by = serializers.PrimaryKeyRelatedField(read_only=True)

    def validate(self, attrs) -> dict:
        attrs = super().validate(attrs)
        if self.instance is None:
            attrs.update({
                'created_by': self.context['request'].user
            })
        else:
            attrs.update({
                'last_modified_by': self.context['request'].user
            })
        return attrs


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = '__all__'

    def _validate_file_size(self, file_content):
        if file_content.size > Attachment.MAX_FILE_SIZE:
            raise serializers.ValidationError(
                gettext('Filesize should be less than: %s. Current is: %s') % (
                    filesizeformat(Attachment.MAX_FILE_SIZE),
                    filesizeformat(file_content.size),
                )
            )

    def _validate_mimetype(self, mimetype):
        if mimetype not in Attachment.ALLOWED_MIMETYPES:
            raise serializers.ValidationError(gettext('Filetype not allowed: %s') % mimetype)

    def validate(self, attrs) -> dict:
        attachment = attrs['attachment']
        self._validate_file_size(attachment)
        byte_stream = attachment.file.read()
        with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
            attrs['mimetype'] = m.id_buffer(byte_stream)
            self._validate_mimetype(attrs['mimetype'])
        with magic.Magic(flags=magic.MAGIC_MIME_ENCODING) as m:
            attrs['encoding'] = m.id_buffer(byte_stream)
        with magic.Magic() as m:
            attrs['filetype_detail'] = m.id_buffer(byte_stream)
        return attrs


class SourcePreviewSerializer(MetaInformationSerializerMixin,
                              serializers.ModelSerializer):
    class Meta:
        model = SourcePreview
        fields = '__all__'

    def create(self, validated_data):
        filter_params = dict(
            url=validated_data['url'],
            created_by=validated_data['created_by'],
            status=SourcePreview.PREVIEW_STATUS.IN_PROGRESS,
            created_at__gte=timezone.now() - timedelta(seconds=PDF_TASK_TIMEOUT)
        )

        if SourcePreview.objects.filter(
            **filter_params
        ).exists():
            return SourcePreview.objects.filter(
                **filter_params
            ).first()
        return SourcePreview.get_pdf(validated_data)

    def update(self, instance, validated_data):
        return SourcePreview.get_pdf(validated_data, instance=instance)


class ExcelDownloadSerializer(MetaInformationSerializerMixin,
                              serializers.ModelSerializer):
    model_instance_id = serializers.IntegerField(required=False)

    class Meta:
        model = ExcelDownload
        fields = '__all__'

    def validate_concurrent_downloads(self, attrs: dict) -> None:
        if ExcelDownload.objects.filter(
            status__in=[
                ExcelDownload.EXCEL_GENERATION_STATUS.PENDING,
                ExcelDownload.EXCEL_GENERATION_STATUS.IN_PROGRESS
            ],
            created_by=self.context['request'].user,
        ).count() >= settings.EXCEL_EXPORT_CONCURRENT_DOWNLOAD_LIMIT:
            raise serializers.ValidationError(gettext(
                'Only %s excel export(s) is allowed at a time'
            ) % settings.EXCEL_EXPORT_CONCURRENT_DOWNLOAD_LIMIT, code='limited-at-a-time')

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        self.validate_concurrent_downloads(attrs)
        return attrs

    def create(self, validated_data):
        model_instance_id = validated_data.pop("model_instance_id", None)
        instance = super().create(validated_data)
        instance.trigger_excel_generation(self.context['request'], model_instance_id=model_instance_id)
        return instance


class UpdateSerializerMixin:
    """Makes all fields not required apart from the id field"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # all updates will be a patch update
        for name in self.fields:
            self.fields[name].required = False
        self.fields['id'].required = True


class ClientSerializer(
    MetaInformationSerializerMixin,
    serializers.ModelSerializer
):
    class Meta:
        model = Client
        fields = (
            'id',
            'name',
            'code',
            'is_active',
        )


class ClientUpdateSerializer(UpdateSerializerMixin, ClientSerializer):
    id = IntegerIDField(required=True)


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
        instance = super().create(validated_data)
        transaction.on_commit(
            lambda: run_bulk_api_operation(instance.pk)
        )
        return instance

    def update(self, *_):
        raise serializers.ValidationError(gettext('Update not allowed'))
