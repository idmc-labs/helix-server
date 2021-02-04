import mimetypes
import magic

from rest_framework import serializers

from apps.contrib.models import Attachment
from apps.contrib.models import SourcePreview


class MetaInformationSerializerMixin(object):
    """
    Responsible to add following fields into the validated data
    - created_by
    - last_modified_by
    """

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

    def validate(self, attrs) -> dict:
        attachment = attrs['attachment']
        byte_stream = attachment.file.read()
        with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
            attrs['mimetype'] = m.id_buffer(byte_stream)
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
        return SourcePreview.get_pdf(**validated_data)

    def update(self, instance, validated_data):
        return SourcePreview.get_pdf(**validated_data, instance=instance)