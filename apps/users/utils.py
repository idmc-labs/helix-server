from typing import Union

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import DjangoUnicodeDecodeError
from djoser.compat import get_user_email
from djoser.email import ActivationEmail
from djoser.utils import decode_uid
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from django.utils.translation import gettext


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

def encode_reset_password_token(user_id):
    # generate a password reset token with user's id and token created date
    return urlsafe_base64_encode(force_bytes(f"{user_id},{timezone.now() + timedelta(hours=24)}"))

def decode_reset_password_token(password_reset_token):
    # Decode token and parse token expiry time
    try:
        decoded_data = force_text(urlsafe_base64_decode(password_reset_token)).split(',')
        return {'user_id': decoded_data[0], 'token_expiry_time': parse_datetime(decoded_data[1])}
    except (TypeError, ValueError, IndexError):
        raise serializers.ValidationError(gettext('Invalid token supplied'))
