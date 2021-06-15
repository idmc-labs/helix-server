from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'apps.users'

    def ready(self):

        super().ready()

        from apps.users import receivers  # noqa: F401
