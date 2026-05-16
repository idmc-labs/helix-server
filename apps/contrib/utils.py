import gzip
from io import BytesIO

import magic
from botocore.exceptions import ClientError
from django.conf import settings
from django.db.models import FileField
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

    def get_bucket_name(self) -> str:
        return self.storage.bucket.name

    def generate_s3_key_for_file(self, file: FileField) -> str:
        # https://github.com/jschneier/django-storages/blob/ca89a94a7462a2423df460e7bfd5f847457042ca/storages/backends/s3.py#L530
        return self.storage._normalize_name(clean_name(file.name))

    def verify_uploaded(self) -> dict:
        if self.instance.created_by != self.context["request"].user:
            raise BigFileUploadVerificationException(gettext(PERMISSION_DENIED_MESSAGE))

        if self.instance.is_file_uploaded:
            raise BigFileUploadVerificationException(gettext("Attachment is already marked as uploaded."))
        try:
            file_size = self.instance.attachment.size
            obj = self.storage.bucket.meta.client.get_object(
                Bucket=self.get_bucket_name(),
                Key=self.generate_s3_key_for_file(self.instance.attachment),
                Range="bytes=0-4095",  # only first 4KB
            )

            data = obj["Body"].read()

            # When ``AWS_IS_GZIPPED=True`` + the object's content type is in
            # ``GZIP_CONTENT_TYPES`` (PDFs are by default), django-storages
            # uploads the object with ``Content-Encoding: gzip`` — so a Range
            # GET returns the *raw* gzipped bytes (boto3 does not auto-decode
            # for Range requests). Decompress before sniffing or libmagic
            # reports the gzip wrapper instead of the real content type.
            if (obj.get("ContentEncoding") or "").lower() == "gzip":
                try:
                    with gzip.GzipFile(fileobj=BytesIO(data)) as gzf:
                        decoded = gzf.read(4096)
                    if decoded:
                        data = decoded
                except (OSError, EOFError):
                    # Truncated gzip stream — leave ``data`` as-is so the
                    # error message below is the actual gzip-detection
                    # outcome rather than a swallowed exception.
                    pass

            with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
                mime_type = m.id_buffer(data)
                if mime_type not in Attachment.ALLOWED_MIMETYPES:
                    raise BigFileUploadVerificationException(f"Invalid attachment type, {mime_type}")
            return dict(file_size=file_size, mimetype=mime_type)
        except BigFileUploadVerificationException:
            # Don't bury the specific reason ("Invalid attachment type, …")
            # under the catch-all below.
            raise
        except Exception as e:
            raise BigFileUploadVerificationException(f"File verification was failed: {e}") from e

    def get_attachment_presigned_url(self) -> str:
        presigned_url = None
        try:
            presigned_url = self.storage.bucket.meta.client.generate_presigned_url(
                ClientMethod="put_object",
                HttpMethod="PUT",
                Params={
                    "Bucket": self.get_bucket_name(),
                    "Key": self.generate_s3_key_for_file(self.instance.attachment),
                    "ContentType": self.instance.mimetype,
                },
                ExpiresIn=settings.S3_OBJECT_PRESIGNED_URL_TTL,
            )
        except (ClientError, Exception) as e:
            raise Exception("Exceptation: Couldn't construct pre-signed url") from e

        return presigned_url
