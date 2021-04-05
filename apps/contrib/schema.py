import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import (
    DjangoObjectField
)

from apps.contrib.models import Attachment
from apps.contrib.enums import AttachmentForGrapheneEnum


class AttachmentType(DjangoObjectType):
    class Meta:
        model = Attachment

    attachment_for = graphene.Field(AttachmentForGrapheneEnum)

    def resolve_attachment(root, info, **kwargs):
        return info.context.request.build_absolute_uri(root.attachment.url)


class Query:
    attachment = DjangoObjectField(AttachmentType)
