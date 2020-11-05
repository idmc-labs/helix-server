import django_filters

from apps.entry.models import Entry


class EntryFilter(django_filters.FilterSet):
    article_title_contains = django_filters.CharFilter(field_name='article_title', lookup_expr='icontains')

    class Meta:
        model = Entry
        fields = ['event']

