from django.apps import AppConfig


class ReviewConfig(AppConfig):
    name = 'apps.review'

    def ready(self):
        # registering receiver
        from apps.review import receivers  # noqa f401
