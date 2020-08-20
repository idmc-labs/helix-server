import graphene

from apps.contact.models import Contact, Communication

DesignationGrapheneEnum = graphene.Enum.from_enum(Contact.DESIGNATION)
GenderGrapheneEnum = graphene.Enum.from_enum(Contact.GENDER)
CommunicationMediumGrapheneEnum = graphene.Enum.from_enum(Communication.COMMUNICATION_MEDIUM)
