import magic
import random
import string
from datetime import timedelta
from django.utils import timezone

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext
from rest_framework import serializers

from utils.serializers import IntegerIDField
from apps.entry.tasks import PDF_TASK_TIMEOUT
from apps.contrib.models import (
    Attachment,
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
            'is_active',
            'acronym',
            'contact_name',
            'contact_email',
            'contact_website',
            'use_case',
            'other_notes',
            'opted_out_of_emails',
        )
        read_only_fields = (
            'code',
            'created_by',
            'created_at',
            'last_modified_by',
            'modified_at',
        )

    def create(self, validated_data):
        # Generate a random alphanumeric key of length 16
        validated_data['code'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        # Set the user who created the client
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Check if the client is being revoked
        if 'revoked_by' in validated_data and validated_data['revoked_by'] is not None:
            # Set the revoked_at field to the current datetime if it's being revoked
            instance.revoked_at = timezone.now()
        return super().update(instance, validated_data)


class ClientUpdateSerializer(UpdateSerializerMixin, ClientSerializer):
    id = IntegerIDField(required=True)
