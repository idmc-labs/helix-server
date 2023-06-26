from rest_framework import status
from django.core.exceptions import ValidationError


class GraphqlNotAllowedException(ValidationError):
    code = status.HTTP_405_METHOD_NOT_ALLOWED
