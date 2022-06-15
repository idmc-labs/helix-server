__all__ = ['OrganizationCategoryTypeGrapheneEnum']

import graphene

from apps.organization.models import Organization, OrganizationKind

from utils.enums import enum_description

OrganizationCategoryTypeGrapheneEnum = graphene.Enum.from_enum(
    Organization.ORGANIZATION_CATEGORY,
    description=enum_description
)

OrganizationReliablityEnum = graphene.Enum.from_enum(
    OrganizationKind.ORGANIZATION_RELIABILITY,
    description=enum_description
)
enum_map = dict(
    ORGANIZATION_CATEGORY=OrganizationCategoryTypeGrapheneEnum,
    ORGANIZATION_RELIABILITY=OrganizationReliablityEnum,
)
