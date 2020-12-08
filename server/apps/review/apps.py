from django.apps import AppConfig


class ReviewConfig(AppConfig):
    name = 'apps.review'

    def ready(self):
        # registering receiver
        import apps.review.receivers
