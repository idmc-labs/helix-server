from botocore.exceptions import ClientError
from django.conf import settings

from apps.contrib.models import Attachment
from helix.storages import S3MediaStorage


class AttachmentBoto3ConnectorService(object):
    def __init__(self, instance: Attachment):
        self.storage = S3MediaStorage()
        self.instance = instance

    def verify_uploaded(self) -> Attachment:
        if self.instance.is_file_uploaded:
            raise ValueError("Attachment is already marked as uploaded.")
        try:
            response = self.storage.bucket.meta.client.head_object(
                Bucket=self.storage.bucket.name,
                Key=self.instance.attachment.name,
            )
        except self.storage.bucket.meta.client.exceptions.NoSuchKey as e:
            raise Exception(f"File has not been uploaded; {e}")
        except ClientError as e:
            raise Exception(f"Could not read head object, {e}")
        except Exception as e:
            raise Exception(f"Unknown error; {str(e)}")

        mime_type = response["ContentType"]

        if mime_type not in Attachment.ALLOWED_MIMETYPES:
            raise Exception(f"Invalid attachment type, {mime_type}")

        self.instance.mimetype = mime_type
        self.instance.is_file_uploaded = True
        self.instance.file_size = response["ContentLength"]
        self.instance.save(
            update_fields=[
                "file_size",
                "mimetype",
                "is_file_uploaded",
            ],
        )

        return self.instance

    def get_attachment_presigned_url(self) -> str:
        presigned_url = "N/A"
        try:
            presigned_url = self.storage.bucket.meta.client.generate_presigned_url(
                ClientMethod="put_object",
                HttpMethod="PUT",
                Params={
                    "Bucket": self.storage.bucket.name,
                    "Key": self.instance.attachment.name,
                    "ContentType": self.instance.mimetype,
                },
                ExpiresIn=getattr(settings, "S3_OBJECT_PRESIGNED_URL_TTL", 3600),
            )
        except (ClientError, Exception) as e:
            raise Exception(f"Exceptation: Couldn't construct pre-signed url, {e}")

        return presigned_url
