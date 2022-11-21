from utils.graphene.enums import (
    convert_enum_to_graphene_enum,
    get_enum_name_from_django_field,
)

from apps.notification.models import Notification

NotificationTypeEnum = convert_enum_to_graphene_enum(Notification.Type, name='NotificationTypeEnum')

enum_map = {
    get_enum_name_from_django_field(field): enum
    for field, enum in (
        (Notification.type, NotificationTypeEnum),
    )
}
