import django_filters

from apps.entry.models import Entry


class EntryFilter(django_filters.FilterSet):
    class Meta:
        model = Entry
        fields = {
            'article_title': ('icontains',),
        }
