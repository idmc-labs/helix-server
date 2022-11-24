from utils.graphene.enums import (
    convert_enum_to_graphene_enum,
)

from apps.notification.models import Notification

NotificationTypeEnum = convert_enum_to_graphene_enum(Notification.Type, name='NotificationTypeEnum')

enum_map = dict(
    NotificationTypeEnum=NotificationTypeEnum
)
