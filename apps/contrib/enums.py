import graphene

from apps.contrib.models import Attachment, SourcePreview

from apps.contact.enums import enum_map as contact_enums
from apps.crisis.enums import enum_map as crisis_enums
from apps.entry.enums import enum_map as entry_enums
from apps.event.enums import enum_map as event_enums
from apps.parking_lot.enums import enum_map as parking_enums
from apps.review.enums import enum_map as review_enums
from apps.users.enums import enum_map as user_enums
from utils.enums import enum_description

AttachmentForGrapheneEnum = graphene.Enum.from_enum(Attachment.FOR_CHOICES,
                                                    description=enum_description)
PreviewStatusGrapheneEnum = graphene.Enum.from_enum(SourcePreview.PREVIEW_STATUS,
                                                    description=enum_description)

enum_map = dict(
    FOR_CHOICES=AttachmentForGrapheneEnum
)

ENUM_TO_GRAPHENE_ENUM_MAP = {
    **enum_map,
    **contact_enums,
    **crisis_enums,
    **entry_enums,
    **event_enums,
    **parking_enums,
    **review_enums,
    **user_enums,
}
