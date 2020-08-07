from djoser.compat import get_user_email
from djoser.email import ActivationEmail


def send_activation_email(user, request):
    to = [get_user_email(user)]
    ActivationEmail(request, {'user': user}).send(to)
