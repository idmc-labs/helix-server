from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from djoser.compat import get_user_email
from djoser.email import ActivationEmail
from djoser.utils import decode_uid

User = get_user_model()


def send_activation_email(user, request):
    to = [get_user_email(user)]
    ActivationEmail(request, {'user': user}).send(to)


def activation_token_is_valid(uid, token):
    uid = decode_uid(uid)
    user = User.objects.get(pk=uid)
    if not default_token_generator.check_token(user, token):
        return False
    return user
