from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.users.enums import USER_ROLE
from apps.users.models import Portfolio


class Command(BaseCommand):
    help = 'Create dummy users.'

    def add_arguments(self, parser):
        parser.add_argument('firstname', type=str)
        parser.add_argument('lastname', type=str)
        parser.add_argument('email', type=str)
        parser.add_argument('password', type=str)
        parser.add_argument('role', type=str)

    def handle(self, *args, **options):
        User = get_user_model()

        user, _ = User.objects.get_or_create(
            email=options['email'],
        )
        user.username = options['email']
        user.first_name = options['firstname']
        user.last_name = options['lastname']
        user.set_password(options['jassword'])
        user.save()

        role = USER_ROLE.ADMIN if options['role'] == 'admin' else USER_ROLE.GUEST

        Portfolio.objects.get_or_create(
            user=user,
            role=role,
        )
