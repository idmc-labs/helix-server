import django_filters
from django.db.models import Value
from django.db.models.functions import Lower, StrIndex

from apps.contextualupdate.models import ContextualUpdate
from apps.crisis.models import Crisis
from utils.filters import StringListFilter


class ContextualUpdateFilter(django_filters.FilterSet):
    article_title = django_filters.CharFilter(method='filter_article_title')
    countries = StringListFilter(method='filter_countries')
    sources = StringListFilter(method='filter_sources')
    publishers = StringListFilter(method='filter_publishers')
    crisis_types = StringListFilter(method='filter_crisis_types')

    class Meta:
        model = ContextualUpdate
        fields = {
            'publish_date': ['lte', 'gte'],
        }

    def filter_article_title(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            lname=Lower('article_title')
        ).annotate(
            idx=StrIndex('lname', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'name')

    def filter_m2m(self, qs, field_name, value):
        if not value:
            return qs
        filter_param = {
            f'{field_name}__in': value
        }
        return qs.filter(**filter_param).distinct()

    def filter_countries(self, qs, name, value):
        return self.filter_m2m(qs, 'countries', value)

    def filter_sources(self, qs, name, value):
        return self.filter_m2m(qs, 'sources', value)

    def filter_publishers(self, qs, name, value):
        return self.filter_m2m(qs, 'publishers', value)

    def filter_crisis_types(self, qs, name, value):
        if value:
            return qs.filter(status__in=[Crisis.CRISIS_TYPE.get(each) for each in value])
        return qs
