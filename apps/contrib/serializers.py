from datetime import datetime, timedelta
import magic

from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext
from rest_framework import serializers

from apps.entry.tasks import DRAMATIQ_TIMEOUT
from apps.contrib.models import (
    Attachment,
    SourcePreview,
    ExcelDownload,
)


class IntegerIDField(serializers.IntegerField):
    """
    This field is created to override the graphene conversion of the integerfield
    """
    pass


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
                gettext('Filesize is greater than: %s. Current is: %s') % (
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
            created_at__gte=datetime.now() - timedelta(seconds=DRAMATIQ_TIMEOUT)
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
    class Meta:
        model = ExcelDownload
        fields = '__all__'

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.trigger_excel_generation(self.context['request'])
        return instance


class UpdateSerializerMixin:
    """Makes all fields not required apart from the id field"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # all updates will be a patch update
        for name in self.fields:
            self.fields[name].required = False
        self.fields['id'].required = True
