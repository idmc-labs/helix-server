from django.apps import AppConfig


class ReviewConfig(AppConfig):
    name = 'apps.review'

    def ready(self):
        # registering receiver
        pass
