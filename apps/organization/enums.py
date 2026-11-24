__all__ = ["OrganizationCategoryTypeGrapheneEnum"]

import graphene

from apps.organization.models import Organization, SourceType
from utils.enums import enum_description

OrganizationCategoryTypeGrapheneEnum = graphene.Enum.from_enum(
    Organization.ORGANIZATION_CATEGORY, description=enum_description
)

SourceTypeLevelEnum = graphene.Enum.from_enum(SourceType.SOURCE_TYPE_CLASSIFICATION, description=enum_description)

enum_map = dict(
    ORGANIZATION_CATEGORY=OrganizationCategoryTypeGrapheneEnum,
    SOURCE_TYPE_CLASSIFICATION=SourceTypeLevelEnum,
)
