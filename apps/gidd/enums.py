from utils.graphene.enums import (
    convert_enum_to_graphene_enum,
)

from apps.gidd.models import GiddLog

GiddLogStatusEnum = convert_enum_to_graphene_enum(GiddLog.Status, name='GiddLogStatusTypeEnum')

enum_map = dict(
    GiddLogStatusEnum=GiddLogStatusEnum
)
