from django_filters import rest_framework as df
from utils.filters import IDListFilter, StringListFilter
from apps.notification.models import Notification


class NotificationFilter(df.FilterSet):
    events = IDListFilter(method='filter_events')
    figures = IDListFilter(method='filter_figures')

    def filter_events(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(event__in=value)

    def filter_figures(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(figure__in=value)

    class Meta:
        model = Notification
        fields = ()
