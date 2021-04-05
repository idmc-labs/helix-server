import django_filters

from apps.event.models import Event
from apps.crisis.models import Crisis
from utils.filters import StringListFilter


class EventFilter(django_filters.FilterSet):
    name_contains = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    filter_event_types = StringListFilter(method='filter_event_types')

    class Meta:
        model = Event
        fields = ['crisis']

    def filter_event_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # internal filtering
                return qs.filter(event_type__in=value).distinct()
            else:
                # client side filtering
                return qs.filter(event_type__in=[
                    Crisis.CRISIS_TYPE.get(item).value for item in value
                ])
        return qs
