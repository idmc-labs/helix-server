from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = "apps.common"

    def ready(self):
        from helix.pg_functions import register_lookups

        register_lookups()
