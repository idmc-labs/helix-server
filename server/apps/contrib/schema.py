import graphene
from graphene_django import DjangoObjectType
from graphene.types.utils import get_type
from graphene_django_extras import (
    PageGraphqlPagination, 
    DjangoObjectField
)

from apps.contrib.models import Attachment


class AttachmentType(DjangoObjectType):
    class Meta:
        model = Attachment

    def resolve_attachment(root, info, **kwargs):
        return root.attachment.url


class Query:
    attachment = DjangoObjectField(AttachmentType)

