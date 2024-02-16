from typing import Union
from contextlib import contextmanager

from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import DjangoUnicodeDecodeError
from django.conf import settings
from djoser.compat import get_user_email
from djoser.email import ActivationEmail
from djoser.utils import decode_uid

from apps.users.models import User, Portfolio


def send_activation_email(user, request) -> None:
    to = [get_user_email(user)]
    ActivationEmail(request, {'user': user}).send(to)


def get_user_from_activation_token(uid, token) -> Union[User, None]:
    try:
        uid = decode_uid(uid)
    except DjangoUnicodeDecodeError:
        return None
    try:
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError):
        return None
    if not default_token_generator.check_token(user, token):
        return None
    return user


class HelixInternalBot:
    user: User

    def __init__(self):
        # TODO: We need to flag bounce email if we send email in future
        self.user, _ = User.objects.get_or_create(email=settings.INTERNAL_BOT_EMAIL)

    @contextmanager
    def temporary_role(self, role):
        temp_role, _ = Portfolio.objects.get_or_create(
            user=self.user,
            role=role,
        )
        try:
            yield temp_role
        finally:
            temp_role.delete()
