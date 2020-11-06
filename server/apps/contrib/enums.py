import graphene

from apps.contrib.models import Attachment

from utils.enums import enum_description

AttachmentForGrapheneEnum = graphene.Enum.from_enum(Attachment.FOR_CHOICES, description=enum_description)

