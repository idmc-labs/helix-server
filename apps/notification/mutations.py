import graphene
from django.utils.translation import gettext
from apps.notification.models import Notification
from utils.error_types import CustomErrorType
from apps.notification.schema import GenericNotificationType


class ToggleNotificationRead(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    result = graphene.Field(GenericNotificationType)

    @staticmethod
    def mutate(root, info, id):
        instance = Notification.objects.filter(
            recipient=info.context.user,
            id=id
        ).first()
        if not instance:
            return ToggleNotificationRead(
                errors=[
                    dict(field='nonFieldErrors',
                         messages=gettext('Notification does not exist or you are not recipient.'))
                ],
                ok=False
            )
        if not instance.is_read:
            instance.is_read = True
        else:
            instance.is_read = False
        instance.save()
        return ToggleNotificationRead(result=instance, errors=None, ok=True)


class Mutation(object):
    toggle_notification_read = ToggleNotificationRead.Field()
