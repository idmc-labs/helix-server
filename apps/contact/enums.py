__all__ = ['DesignationGrapheneEnum', 'CommunicationMediumGrapheneEnum']

import graphene

from apps.contact.models import Contact, Communication

from utils.enums import enum_description
# from apps.common.enums import GENDER_TYPE

DesignationGrapheneEnum = graphene.Enum.from_enum(Contact.DESIGNATION, description=enum_description)
# GenderGrapheneEnum = graphene.Enum.from_enum(GENDER_TYPE, description=enum_description)
CommunicationMediumGrapheneEnum = graphene.Enum.from_enum(Communication.COMMUNICATION_MEDIUM,
                                                          description=enum_description)

enum_map = dict(
    DESIGNATION=DesignationGrapheneEnum,
    # GENDER_TYPE=GenderGrapheneEnum,
    COMMUNICATION_MEDIUM=CommunicationMediumGrapheneEnum
)
