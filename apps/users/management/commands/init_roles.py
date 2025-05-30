from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from apps.users.roles import PERMISSIONS, USER_ROLES


class Command(BaseCommand):
    help = "Initialize or update roles."

    def handle(self, *args, **options):
        for role in USER_ROLES:
            group, created = Group.objects.get_or_create(name=role.name)
            permissions = []
            for action, models in PERMISSIONS[role].items():
                permissions.extend([Permission.objects.get(codename=f"{action.name}_{model.name}") for model in models])
            group.permissions.set(permissions)
            self.stdout.write(
                self.style.SUCCESS(f"{'Created' if created else 'Updated'} {role.name} with {len(permissions)} permissions.")
            )
