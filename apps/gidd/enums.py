from utils.graphene.enums import (
    convert_enum_to_graphene_enum,
)

from apps.gidd.models import StatusLog

GiddStatusLogEnum = convert_enum_to_graphene_enum(StatusLog.Status, name='GiddStatusLogTypeEnum')

enum_map = dict(
    GiddLogStatusEnum=GiddStatusLogEnum
)
