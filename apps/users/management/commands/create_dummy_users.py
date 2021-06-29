from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.users.enums import USER_ROLE
from apps.users.models import Portfolio


class Command(BaseCommand):
    help = 'Create dummy users.'

    def handle(self, *args, **options):
        User = get_user_model()
        raw_password = 'admin123'
        roles = [('admin', USER_ROLE.ADMIN, 'Eric', 'Lowe'),
                 ('guest', USER_ROLE.GUEST, 'Frederick', 'Gutierrez')]

        for username, role, first_name, last_name in roles:
            email = f'{username}@idmcdb.org'
            user, _ = User.objects.get_or_create(
                email=email,
            )
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.set_password(raw_password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'{role.name} created with email: '
                                                 f'{email} password: {raw_password}'))
            try:
                Portfolio.objects.get_or_create(
                    user=user,
                    role=role,
                )
                self.stdout.write(self.style.SUCCESS(f'Added portfolio for {role.name}\n'))
            except Exception as e:
                print('Failed here...', email, e, ' << Ignore me\n')
