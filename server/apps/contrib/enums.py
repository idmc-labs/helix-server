import graphene

from apps.contrib.models import Attachment, SourcePreview

from utils.enums import enum_description

AttachmentForGrapheneEnum = graphene.Enum.from_enum(Attachment.FOR_CHOICES,
                                                    description=enum_description)
PreviewStatusGrapheneEnum = graphene.Enum.from_enum(SourcePreview.PREVIEW_STATUS,
                                                    description=enum_description)
