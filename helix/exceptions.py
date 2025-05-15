from django.core.exceptions import ValidationError
from rest_framework import status


class GraphqlNotAllowedException(ValidationError):
    code = status.HTTP_405_METHOD_NOT_ALLOWED
