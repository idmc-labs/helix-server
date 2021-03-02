import hashlib
from typing import List, Callable
import logging

from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext

PERMISSION_DENIED_MESSAGE = 'You do not have permission to perform this action.'

logger = logging.getLogger(__name__)


def permission_checker(perms: List[str]) -> Callable[..., Callable]:
    def wrapped(func):
        def wrapped_func(root, info, *args, **kwargs):
            if not info.context.user.has_perms(perms):
                raise PermissionDenied(gettext(PERMISSION_DENIED_MESSAGE))
            return func(root, info, *args, **kwargs)
        return wrapped_func
    return wrapped


def is_authenticated() -> Callable[..., Callable]:
    def wrapped(func):
        def wrapped_func(root, info, *args, **kwargs):
            if not info.context.user.is_authenticated:
                raise PermissionDenied(gettext(PERMISSION_DENIED_MESSAGE))
            return func(root, info, *args, **kwargs)
        return wrapped_func
    return wrapped


def cache_key_function(*args, **kwargs):
    logger.error('cache key')
    return hashlib.sha256((str(args) + str(kwargs)).encode()).hexdigest()


def cache_me(timeout=None):
    def wrapped(func):
        def wrapped_func(*args, **kwargs):
            cache_key = cache_key_function(func.__name__, *args, **kwargs)
            cached_value = cache.get(cache_key)
            if cached_value:
                return cached_value
            value = func(*args, **kwargs)
            cache.set(cache_key, value, timeout)
            return value
        return wrapped_func
    return wrapped
