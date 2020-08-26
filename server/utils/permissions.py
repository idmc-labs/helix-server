from typing import List, Callable

from django.core.exceptions import PermissionDenied


def permission_checker(perms: List[str]) -> Callable[..., Callable]:
    def wrapped(func):
        def wrapped_func(root, info, *args, **kwargs):
            if not info.context.user.has_perms(perms):
                raise PermissionDenied('You do not have permission to perform this action.')
            return func(root, info, *args, **kwargs)
        return wrapped_func
    return wrapped
