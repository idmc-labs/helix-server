import django_filters

from apps.event.models import Event


class EventFilter(django_filters.FilterSet):
    name_contains = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Event
        fields = ['crisis']
