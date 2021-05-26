from django.apps import AppConfig


class EntryConfig(AppConfig):
    name = 'apps.entry'

    def ready(self):
        # registering receiver
        from apps.entry import receivers  # noqa :f401
