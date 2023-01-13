from django.apps import AppConfig


class ReportConfig(AppConfig):
    name = 'apps.report'

    def ready(self):
        from apps.report import receivers # noqa :f401
