import graphene
from apps.notification.models import Notification
from utils.enums import enum_description

NotificationTypeEnum = graphene.Enum.from_enum(Notification.NotificationType, description=enum_description)

enum_map = dict(
    NotificationTypeEnum=NotificationTypeEnum,
)
