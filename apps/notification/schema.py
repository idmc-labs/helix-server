import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField

from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount
from utils.graphene.enums import EnumDescription

from apps.notification.models import Notification
from apps.notification.enums import NotificationTypeEnum
from apps.notification.filters import NotificationFilter


def notificaiton_qs(info):
    return Notification.objects.filter(recipient=info.context.user)


class GenericNotificationType(DjangoObjectType):
    class Meta:
        model = Notification
        fields = (
            'id',
            'notification_type',
            'recipient',
            'event',
            'figure',
            'is_read',
            'created_at',
        )

    notification_type = graphene.Field(NotificationTypeEnum)
    notification_type_display = EnumDescription(source='get_notification_type')

    @staticmethod
    def get_custom_queryset(queryset, info):
        return notificaiton_qs(info)


class GenericNotificationListType(CustomDjangoListObjectType):
    class Meta:
        model = Notification
        filterset_class = NotificationFilter


class Query(object):
    notification = DjangoObjectField(GenericNotificationType)
    notifications = DjangoPaginatedListObjectField(
        GenericNotificationListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        )
    )

    @staticmethod
    def resolve_notifications(root, info, **kwargs):
        if info.context.user.is_authenticated:
            return notificaiton_qs(info)
        return None
