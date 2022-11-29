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
            'type',
            'recipient',
            'actor',
            'event',
            'figure',
            'is_read',
            'created_at',
        )

    type = graphene.Field(NotificationTypeEnum)
    type_display = EnumDescription(source='get_type_display')

    @staticmethod
    def get_custom_queryset(queryset, info):
        # FIXME: Improve utils
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
        ),
    )

    def resolve_notification(root, info, **kwargs):
        # FIXME: This resolver does not work, improve utils to fix this
        if info.context.user.is_authenticated:
            return notificaiton_qs(info)
        return []
