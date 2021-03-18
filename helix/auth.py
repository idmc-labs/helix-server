from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext

PERMISSION_DENIED_MESSAGE = 'You do not have permission to perform this action.'


class WhiteListMiddleware:
    def resolve(self, next, root, info, **args):
        # if user is not authenticated and user is not accessing
        # whitelisted nodes, then return none
        if not info.context.user.is_authenticated:
            if info.field_name not in settings.GRAPHENE_NODES_WHITELIST:
                raise PermissionDenied(gettext(PERMISSION_DENIED_MESSAGE))
        return next(root, info, **args)
