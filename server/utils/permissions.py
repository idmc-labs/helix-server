from typing import List

from django.core.exceptions import PermissionDenied


def permission_checker(info, perms: List[str]) -> None:
    if not info.context.user.has_perms(perms):
        raise PermissionDenied('You do not have permission to do that.')
