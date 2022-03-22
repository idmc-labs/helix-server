from django.contrib.auth.models import Permission, Group
from django.core.management.base import BaseCommand

from apps.users.roles import USER_ROLES, PERMISSIONS


class Command(BaseCommand):
    help = 'Initialize or update roles.'

    def handle(self, *args, **options):
        permission_queryset = Permission.objects.exclude(content_type__app_label='helixmigration')
        for role in USER_ROLES:
            group, created = Group.objects.get_or_create(name=role.name)
            permissions = list()
            for action, models in PERMISSIONS[role].items():
                permissions.extend([
                    permission_queryset.get(codename=f'{action.name}_{model.name}') for model in models
                ])
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f'{"Created" if created else "Updated"} '
                                                 f'{role.name} with {len(permissions)} permissions.'))
