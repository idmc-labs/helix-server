from django.apps import AppConfig


class EntryConfig(AppConfig):
    name = 'apps.entry'

    def ready(self):
        from apps.entry import receivers # noqa :f401
