from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.users.roles import ADMIN, MONITORING_EXPERT_EDITOR, MONITORING_EXPERT_REVIEWER, GUEST


class Command(BaseCommand):
    help = 'Create dummy users.'

    def handle(self, *args, **options):
        User = get_user_model()
        raw_password = 'admin123'
        roles = [('admin', ADMIN),
                 ('editor', MONITORING_EXPERT_EDITOR),
                 ('reviewer', MONITORING_EXPERT_REVIEWER),
                 ('guest', GUEST)]

        for name, role in roles:
            email = f'{name}@helix.com'
            user, _ = User.objects.get_or_create(
                username=name,
                email=email
            )
            user.set_password(raw_password)
            user.save()
            user.groups.set([Group.objects.get(name=role)])
            self.stdout.write(self.style.SUCCESS(f'{role} created with email: '
                                                 f'{email} password: {raw_password}'))
