from django_filters import rest_framework as df
from utils.filters import IDListFilter, StringListFilter
from apps.notification.models import Notification


class NotificationFilter(df.FilterSet):
    events = IDListFilter(method='filter_events')
    figures = IDListFilter(method='filter_figures')
    types = StringListFilter(method='filter_types')
    created_at_after = df.DateFilter(method='filter_created_at_after')
    created_at_before = df.DateFilter(method='filter_created_at_before')

    def filter_events(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(event__in=value)

    def filter_figures(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(figure__in=value)

    def filter_types(self, qs, name, value):
        if not value:
            return qs
        if isinstance(value[0], int):
            return qs.filter(type_in=value).distinct()
        return qs.filter(
            type__in=[
                Notification.Type.get(item).value for item in value
            ]
        )

    def filter_created_at_after(self, qs, name, value):
        if value:
            return qs.filter(created_at__gte=value)
        return qs

    def filter_created_at_before(self, qs, name, value):
        if value:
            return qs.filter(created_at__lte=value)
        return qs

    class Meta:
        model = Notification
        fields = {
            'recipient': ['exact', ],
            'is_read': ['exact', ],
        }
