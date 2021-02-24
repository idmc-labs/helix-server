from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.users.enums import USER_ROLE


class Command(BaseCommand):
    help = 'Create dummy users.'

    def handle(self, *args, **options):
        User = get_user_model()
        raw_password = 'admin123'
        roles = [('admin', USER_ROLE.ADMIN.name, 'Eric', 'Lowe'),
                 ('editor', USER_ROLE.MONITORING_EXPERT_EDITOR.name, 'Larissa', 'Stevens'),
                 ('reviewer', USER_ROLE.MONITORING_EXPERT_REVIEWER.name, 'Herman', 'Garza'),
                 ('guest', USER_ROLE.GUEST.name, 'Frederick', 'Gutierrez')]

        for username, role, first_name, last_name in roles:
            email = f'{username}@idmcdb.org'
            user, _ = User.objects.get_or_create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_password(raw_password)
            user.save()
            user.groups.set([Group.objects.get(name=role)])
            self.stdout.write(self.style.SUCCESS(f'{role} created with email: '
                                                 f'{email} password: {raw_password}'))
