import django_filters

from apps.crisis.models import Crisis
from utils.filters import StringListFilter


class CrisisFilter(django_filters.FilterSet):
    countries = StringListFilter(method='filter_countries')
    filter_crisis_types = StringListFilter(method='filter_crisis_types')

    class Meta:
        model = Crisis
        fields = {
            'name': ['icontains']
        }

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries__in=value).distinct()

    def filter_crisis_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # internal filtering
                return qs.filter(crisis_type__in=value).distinct()
            else:
                # client side filtering
                return qs.filter(crisis_type__in=[
                    Crisis.CRISIS_TYPE.get(item).value for item in value
                ])
        return qs
