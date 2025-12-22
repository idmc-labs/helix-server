import logging
import random
import string
from datetime import timedelta

import magic
from django.conf import settings
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from django.utils.translation import gettext
from rest_framework import serializers

from apps.contrib.models import (
    Attachment,
    Client,
    ExcelDownload,
    SourcePreview,
    global_upload_to,
)
from apps.contrib.utils import AttachmentBoto3ConnectorService
from apps.entry.tasks import PDF_TASK_TIMEOUT
from helix.exceptions import BigFileUploadVerificationException
from utils.serializers import IntegerIDField

logger = logging.getLogger(__name__)


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
            attrs.update({"created_by": self.context["request"].user})
        else:
            attrs.update({"last_modified_by": self.context["request"].user})
        return attrs


class MarkBigAttachmentFileUploadedSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = []

    def create(self, validated_data):
        raise serializers.ValidationError(gettext("Creating attachment is disallowed, please use the upload endpoint."))

    def validate(self, attrs):
        try:
            verified_attachment_meta = AttachmentBoto3ConnectorService(
                instance=self.instance, context=self.context
            ).verify_uploaded()
        except BigFileUploadVerificationException as e:
            logger.error("Big attachment upload: unable to verify uploaded file", exc_info=True)
            raise serializers.ValidationError(gettext(str(e))) from e
        except Exception as e:
            logger.error(
                "Big attachment upload: unexpected error while verifying big file upload for attachment id", exc_info=True
            )
            raise serializers.ValidationError(gettext("Unexpected error occured")) from e

        attrs["mimetype"] = verified_attachment_meta["mimetype"]
        attrs["file_size"] = verified_attachment_meta["file_size"]

        return attrs

    def update(self, instance, validated_data):
        instance.mimetype = validated_data["mimetype"]
        instance.is_file_uploaded = True
        instance.file_size = validated_data["file_size"]
        instance.save(
            update_fields=[
                "file_size",
                "mimetype",
                "is_file_uploaded",
            ],
        )
        return instance


class BigAttachmentSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    file_name = serializers.CharField(required=True, write_only=True)
    mimetype = serializers.CharField(required=True, write_only=True)
    s3_presigned_upload_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Attachment
        fields = "__all__"
        read_only_fields = (
            "attachment",
            "encoding",
            "filetype_detail",
            "file_size",
            "is_file_uploaded",
            "created_at",
        )

    def get_s3_presigned_upload_url(self, obj):
        return AttachmentBoto3ConnectorService(instance=obj).get_attachment_presigned_url()

    def create(self, validated_data):
        file_name = validated_data.pop("file_name")
        instance = Attachment(
            attachment_for=validated_data.get("attachment_for"),
            is_file_uploaded=False,
            mimetype=validated_data["mimetype"],
            created_by=validated_data["created_by"],
        )
        instance.attachment.name = global_upload_to(instance, file_name)
        instance.save()

        return instance


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = "__all__"

    def _validate_file_size(self, validated_data, file_content) -> None:
        file_size = file_content.size
        if file_size > settings.DJANGO_MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                gettext("Filesize should be less than: %s. Current is: %s")
                % (
                    filesizeformat(settings.DJANGO_MAX_UPLOAD_SIZE),
                    filesizeformat(file_size),
                )
            )
        validated_data["file_size"] = file_size

    def _validate_mimetype(self, mimetype):
        if mimetype not in Attachment.ALLOWED_MIMETYPES:
            raise serializers.ValidationError({"nonFieldErrors": f"Invalid attachment type, {mimetype}"})

    def validate(self, attrs) -> dict:
        attachment = attrs["attachment"]
        self._validate_file_size(attrs, attachment)
        byte_stream = attachment.file.read()
        with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
            attrs["mimetype"] = m.id_buffer(byte_stream)
            self._validate_mimetype(attrs["mimetype"])
        with magic.Magic(flags=magic.MAGIC_MIME_ENCODING) as m:
            attrs["encoding"] = m.id_buffer(byte_stream)
        with magic.Magic() as m:
            attrs["filetype_detail"] = m.id_buffer(byte_stream)
        return attrs

    def create(self, validated_data):
        validated_data["is_file_uploaded"] = True

        return super().create(validated_data)


class SourcePreviewSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SourcePreview
        fields = "__all__"

    def create(self, validated_data):
        filter_params = dict(
            url=validated_data["url"],
            created_by=validated_data["created_by"],
            status=SourcePreview.PREVIEW_STATUS.IN_PROGRESS,
            created_at__gte=timezone.now() - timedelta(seconds=PDF_TASK_TIMEOUT),
        )

        if SourcePreview.objects.filter(**filter_params).exists():
            return SourcePreview.objects.filter(**filter_params).first()
        return SourcePreview.get_pdf(validated_data)

    def update(self, instance, validated_data):
        return SourcePreview.get_pdf(validated_data, instance=instance)


class ExcelDownloadSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    model_instance_id = serializers.IntegerField(required=False)

    class Meta:
        model = ExcelDownload
        fields = "__all__"

    def validate_concurrent_downloads(self, attrs: dict) -> None:
        if (
            ExcelDownload.objects.filter(
                status__in=[
                    ExcelDownload.EXCEL_GENERATION_STATUS.PENDING,
                    ExcelDownload.EXCEL_GENERATION_STATUS.IN_PROGRESS,
                ],
                created_by=self.context["request"].user,
            ).count()
            >= settings.EXCEL_EXPORT_CONCURRENT_DOWNLOAD_LIMIT
        ):
            raise serializers.ValidationError(
                gettext("Only %s excel export(s) is allowed at a time") % settings.EXCEL_EXPORT_CONCURRENT_DOWNLOAD_LIMIT,
                code="limited-at-a-time",
            )

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        self.validate_concurrent_downloads(attrs)
        return attrs

    def create(self, validated_data):
        model_instance_id = validated_data.pop("model_instance_id", None)
        instance = super().create(validated_data)
        instance.trigger_excel_generation(self.context["request"], model_instance_id=model_instance_id)
        return instance


class UpdateSerializerMixin:
    """Makes all fields not required apart from the id field"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # all updates will be a patch update
        for name in self.fields:
            self.fields[name].required = False
        self.fields["id"].required = True


class ClientSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    """
    Serializer for Client objects, including custom validation and creation logic.
    """

    contact_name = serializers.CharField(required=True)
    contact_email = serializers.EmailField(required=True)
    use_cases = serializers.ListField(
        child=serializers.ChoiceField(choices=Client.USE_CASE_TYPES.choices()),
        required=True,
    )

    class Meta:
        model = Client
        fields = (
            "id",
            "name",
            "is_active",
            "acronym",
            "contact_name",
            "contact_email",
            "contact_website",
            "use_cases",
            "other_notes",
            "opted_out_of_emails",
            "share_source",
        )

    def validate(self, attrs):
        """
        Ensures 'other_notes' is provided when 'Other' is selected in use_cases.
        """
        attrs = super().validate(attrs)
        use_cases = attrs.get("use_cases", [])
        if Client.USE_CASE_TYPES.OTHER.value in use_cases and not attrs.get("other_notes"):
            raise serializers.ValidationError({"other_notes": "Required when 'Other' is selected in use cases."})
        return attrs

    def create(self, validated_data):
        """
        Generates a unique client code before creating a new Client instance.
        """
        validated_data["code"] = self._generate_unique_client_code()
        return super().create(validated_data)

    def _generate_unique_client_code(self, code_length=16, max_attempts=5):
        """
        Generates a unique client code consisting of uppercase letters and digits.

        This method attempts to generate a unique code by combining random uppercase letters and digits.
        It checks the uniqueness of the generated code against existing client codes in the database.
        If a unique code is found within the specified number of attempts, it is returned.
        Otherwise, an exception is raised indicating the failure to generate a unique code.

        Parameters:
        - code_length (int): The length of the code to be generated. Defaults to 16.
        - max_attempts (int): The maximum number of attempts to generate a unique code. Defaults to 5.

        Returns:
        - str: A unique client code.

        Raises:
        - Exception: If a unique code cannot be generated after the specified number of attempts.
        """
        for _ in range(max_attempts):
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=code_length))
            if not Client.objects.filter(code=code).exists():
                return code
        raise Exception("Failed to generate a unique code after several attempts.")


class ClientUpdateSerializer(UpdateSerializerMixin, ClientSerializer):
    id = IntegerIDField(required=True)
