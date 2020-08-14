import graphene

from apps.contact.models import Contact, Communication

DesignationGrapheneEnum = graphene.Enum.from_enum(Contact.DESIGNATION)
CommunicationMediumGrapheneEnum = graphene.Enum.from_enum(Communication.COMMUNICATION_MEDIUM)
