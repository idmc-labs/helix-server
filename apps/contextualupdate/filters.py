import django_filters

from apps.contextualupdate.models import ContextualUpdate
from apps.crisis.models import Crisis
from utils.filters import StringListFilter


class ContextualUpdateFilter(django_filters.FilterSet):
    countries = StringListFilter(method='filter_countries')
    sources = StringListFilter(method='filter_sources')
    publishers = StringListFilter(method='filter_publishers')
    crisis_types = StringListFilter(method='filter_crisis_types')

    class Meta:
        model = ContextualUpdate
        fields = {
            'article_title': ['icontains'],
            'publish_date': ['lte', 'gte'],
        }

    def fitler_m2m(self, qs, field_name, value):
        if not value:
            return qs
        filter_param = {
            f'{field_name}__in': value
        }
        return qs.filter(**filter_param).distinct()

    def filter_countries(self, qs, name, value):
        return self.fitler_m2m(qs, 'countries', value)

    def filter_sources(self, qs, name, value):
        return self.fitler_m2m(qs, 'sources', value)

    def filter_publishers(self, qs, name, value):
        return self.fitler_m2m(qs, 'publishers', value)

    def filter_crisis_types(self, qs, name, value):
        if value:
            return qs.filter(status__in=[Crisis.CRISIS_TYPE.get(each) for each in value])
        return qs
