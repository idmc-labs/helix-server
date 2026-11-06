__all__ = ["OrganizationCategoryTypeGrapheneEnum"]

import graphene

from apps.organization.models import Organization, OrganizationKind, SourceType
from utils.enums import enum_description

OrganizationCategoryTypeGrapheneEnum = graphene.Enum.from_enum(
    Organization.ORGANIZATION_CATEGORY, description=enum_description
)

# NOTE: deprecated, will be removed after A7.2.3 (E7 PR 2). Use SourceTypeLevelEnum instead.
OrganizationReliablityEnum = graphene.Enum.from_enum(OrganizationKind.ORGANIZATION_RELIABILITY, description=enum_description)
SourceTypeLevelEnum = graphene.Enum.from_enum(SourceType.SOURCE_TYPE_CLASSIFICATION, description=enum_description)

enum_map = dict(
    ORGANIZATION_CATEGORY=OrganizationCategoryTypeGrapheneEnum,
    ORGANIZATION_RELIABILITY=OrganizationReliablityEnum,
    SOURCE_TYPE_CLASSIFICATION=SourceTypeLevelEnum,
)
