import gzip
import time
import typing
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

# MinIO/S3 are eventually consistent: right after a server-side copy, an
# immediate read-back can momentarily not see the just-written object
# (read-after-write race). Retry the transient read a few times with a short
# backoff before declaring failure. Keeps total worst-case delay < ~1.5s.
VERIFY_READ_MAX_ATTEMPTS = 4
VERIFY_READ_BACKOFF_BASE = 0.2  # seconds; grows as base * 2**attempt (0.2, 0.4, 0.8)


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

    def _read_with_retry(self, read_fn, *, what: str):
        """Run ``read_fn`` retrying only the transient read-after-write race.

        Retries on ``ClientError`` (e.g. NoSuchKey — the object is not yet
        visible) or when ``read_fn`` returns ``None`` (an empty/incomplete
        read). A non-transient failure — e.g. libmagic rejecting the bytes —
        is raised by the caller *outside* this helper, so it is deliberately
        never retried.
        """
        last_exc = None
        for attempt in range(VERIFY_READ_MAX_ATTEMPTS):
            try:
                result = read_fn()
            except ClientError as e:
                # NoSuchKey and other transient read-after-write failures.
                last_exc = e
            else:
                if result is not None:
                    return result
                # ``None`` — object may not be fully visible yet; treat as transient.
                last_exc = BigFileUploadVerificationException(f"empty read for {what}")
            if attempt < VERIFY_READ_MAX_ATTEMPTS - 1:
                time.sleep(VERIFY_READ_BACKOFF_BASE * (2**attempt))
        raise BigFileUploadVerificationException(
            f"File verification was failed after {VERIFY_READ_MAX_ATTEMPTS} attempts ({what}): {last_exc}"
        ) from last_exc

    def _read_file_size(self):
        """HEAD the object for its size.

        ``FieldFile.size`` issues a HEAD against storage; right after a
        server-side copy that HEAD can momentarily 404 (NoSuchKey) exactly
        like the ranged GET below. This read happens *first* in
        ``verify_uploaded`` — right after the copy — so it is the most
        exposed to the read-after-write delay and must be retried too.
        """
        return self.instance.attachment.size

    def _read_head_bytes(self) -> typing.Optional[tuple]:
        """Range-GET the first 4KB. Returns ``None`` on an empty (transient) read."""
        obj = self.storage.bucket.meta.client.get_object(
            Bucket=self.get_bucket_name(),
            Key=self.generate_s3_key_for_file(self.instance.attachment),
            Range="bytes=0-4095",  # only first 4KB
        )
        data = obj["Body"].read()
        # Empty read — object may not be fully visible yet; signal transient.
        return (obj, data) if data else None

    def verify_uploaded(self) -> dict:
        if self.instance.created_by != self.context["request"].user:
            raise BigFileUploadVerificationException(gettext(PERMISSION_DENIED_MESSAGE))

        if self.instance.is_file_uploaded:
            raise BigFileUploadVerificationException(gettext("Attachment is already marked as uploaded."))
        try:
            file_size = self._read_with_retry(self._read_file_size, what="file size")
            obj, data = self._read_with_retry(self._read_head_bytes, what="head bytes")

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
