from graphene_django import DjangoObjectType
from graphene_django_extras import (
    DjangoObjectField
)

from apps.contrib.models import Attachment


class AttachmentType(DjangoObjectType):
    class Meta:
        model = Attachment

    def resolve_attachment(root, info, **kwargs):
        return info.context.build_absolute_uri(root.attachment.url)


class Query:
    attachment = DjangoObjectField(AttachmentType)
