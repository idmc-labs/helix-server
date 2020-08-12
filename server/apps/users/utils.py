from typing import Union

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import DjangoUnicodeDecodeError
from djoser.compat import get_user_email
from djoser.email import ActivationEmail
from djoser.utils import decode_uid

User = get_user_model()


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
