__all__ = ['DesignationGrapheneEnum', 'GenderGrapheneEnum', 'CommunicationMediumGrapheneEnum']

import graphene

from apps.contact.models import Contact, Communication

from utils.enums import enum_description

DesignationGrapheneEnum = graphene.Enum.from_enum(Contact.DESIGNATION, description=enum_description)
GenderGrapheneEnum = graphene.Enum.from_enum(Contact.GENDER, description=enum_description)
CommunicationMediumGrapheneEnum = graphene.Enum.from_enum(Communication.COMMUNICATION_MEDIUM,
                                                          description=enum_description)

enum_map = dict(
    DESGINATION=DesignationGrapheneEnum,
    GENDER=GenderGrapheneEnum,
    COMMUNICATION_MEDIUM=CommunicationMediumGrapheneEnum
)
