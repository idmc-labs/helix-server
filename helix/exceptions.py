from django.core.exceptions import ValidationError
from rest_framework import status


class GraphqlNotAllowedException(ValidationError):
    code = status.HTTP_405_METHOD_NOT_ALLOWED


class BigFileUploadVerificationException(Exception):
    """Raised when verifying a big file upload and the file hasn't been uploaded yet."""

    def __init__(self, message: str = "File has not been uploaded."):
        super().__init__(message)
