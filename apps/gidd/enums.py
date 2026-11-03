import graphene
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.gidd.models import ReleaseMetadata, StatusLog
from utils.graphene.enums import (
    convert_enum_to_graphene_enum,
)

GiddStatusLogEnum = convert_enum_to_graphene_enum(StatusLog.Status, name="GiddStatusLogTypeEnum")
GiddReleaseEnvironmentsEnum = convert_enum_to_graphene_enum(
    ReleaseMetadata.ReleaseEnvironment, name="GiddReleaseEnvironmentsEnum"
)


enum_map = dict(
    GiddLogStatusEnum=GiddStatusLogEnum,
    GiddReleaseEnvironmentsEnum=GiddReleaseEnvironmentsEnum,
)


class GiddEnumType(graphene.ObjectType):
    gidd_release_meta_data = graphene.Field(GiddReleaseEnvironmentsEnum)


# NOTE: We are creating a separate enum because we are not exposting "OTEHR" in GIDD
class CRISIS_TYPE_PUBLIC(enum.Enum):
    CONFLICT = 0
    DISASTER = 1

    __labels__ = {
        CONFLICT: _("Conflict"),
        DISASTER: _("Disaster"),
    }


# The two displacement metrics a GiddEventDisplacement row carries: `new_displacement` (a flow) and
# `total_displacement` (IDP stock). Not a model column -- a logical selector the events table filters on.
class DISPLACEMENT_TYPE_PUBLIC(enum.Enum):
    NEW_DISPLACEMENT = 0
    IDPS = 1

    __labels__ = {
        NEW_DISPLACEMENT: _("New displacement"),
        IDPS: _("IDPs"),
    }


GiddDisplacementTypeEnum = convert_enum_to_graphene_enum(DISPLACEMENT_TYPE_PUBLIC, name="GiddDisplacementTypeEnum")
