import graphene

from apps.event.models import Event

from utils.enums import enum_description

EventOtherSubTypeEnum = graphene.Enum.from_enum(Event.EVENT_OTHER_SUB_TYPE,
                                                description=enum_description)
