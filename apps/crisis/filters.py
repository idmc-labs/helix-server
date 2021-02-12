import django_filters

from apps.crisis.models import Crisis
from utils.filters import StringListFilter


class CrisisFilter(django_filters.FilterSet):
    countries = StringListFilter(method='filter_countries')

    class Meta:
        model = Crisis
        fields = {
            'name': ['icontains']
        }

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries__in=value).distinct()
