from typing import List, Callable

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

PERMISSION_DENIED_MESSAGE = 'You do not have permission to perform this action.'


def permission_checker(perms: List[str]) -> Callable[..., Callable]:
    def wrapped(func):
        def wrapped_func(root, info, *args, **kwargs):
            if not info.context.user.has_perms(perms):
                raise PermissionDenied(_(PERMISSION_DENIED_MESSAGE))
            return func(root, info, *args, **kwargs)
        return wrapped_func
    return wrapped
