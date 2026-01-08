import magic
from botocore.exceptions import ClientError
from django.conf import settings
from django.utils.translation import gettext
from storages.utils import clean_name

from apps.contrib.models import Attachment
from helix.auth import PERMISSION_DENIED_MESSAGE
from helix.exceptions import BigFileUploadVerificationException
from helix.storages import S3MediaStorage


class AttachmentBoto3ConnectorService(object):
    def __init__(self, instance: Attachment, context: dict = {}):
        self.instance = instance
        self.context = context

        self.storage: S3MediaStorage = self.instance.attachment.storage
        assert isinstance(self.storage, S3MediaStorage), f"Storage should be S3MediaStorage, not {self.storage}"

    def verify_uploaded(self) -> dict:
        if self.instance.created_by != self.context["request"].user:
            raise BigFileUploadVerificationException(gettext(PERMISSION_DENIED_MESSAGE))

        if self.instance.is_file_uploaded:
            raise BigFileUploadVerificationException(gettext("Attachment is already marked as uploaded."))
        try:
            file_size = self.instance.attachment.size
            byte_stream = self.instance.attachment.file.read(4096)
            with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
                mime_type = m.id_buffer(byte_stream)
                if mime_type not in Attachment.ALLOWED_MIMETYPES:
                    raise BigFileUploadVerificationException(f"Invalid attachment type, {mime_type}")
            return dict(file_size=file_size, mimetype=mime_type)
        except Exception as e:
            raise BigFileUploadVerificationException("File verification was failed") from e

    def get_attachment_presigned_url(self) -> str:
        presigned_url = None
        try:
            # https://github.com/jschneier/django-storages/blob/ca89a94a7462a2423df460e7bfd5f847457042ca/storages/backends/s3.py#L530
            s3_file_key = self.storage._normalize_name(clean_name(self.instance.attachment.name))

            presigned_url = self.storage.bucket.meta.client.generate_presigned_url(
                ClientMethod="put_object",
                HttpMethod="PUT",
                Params={
                    "Bucket": self.storage.bucket.name,
                    "Key": s3_file_key,
                    "ContentType": self.instance.mimetype,
                },
                ExpiresIn=settings.S3_OBJECT_PRESIGNED_URL_TTL,
            )
        except (ClientError, Exception) as e:
            raise Exception("Exceptation: Couldn't construct pre-signed url") from e

        return presigned_url
