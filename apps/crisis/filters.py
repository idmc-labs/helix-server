import django_filters

from apps.crisis.models import Crisis
from utils.filters import StringListFilter, NameFilterMixin, IDListFilter


class CrisisFilter(NameFilterMixin, django_filters.FilterSet):
    name = django_filters.CharFilter(method='_filter_name')
    countries = StringListFilter(method='filter_countries')
    crisis_types = StringListFilter(method='filter_crisis_types')
    events = IDListFilter(method='filter_events')

    class Meta:
        model = Crisis
        fields = {
            'created_at': ['lt', 'lte', 'gt', 'gte'],
            'start_date': ['lt', 'lte', 'gt', 'gte'],
            'end_date': ['lt', 'lte', 'gt', 'gte'],
        }

    def filter_events(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(events__in=value).distinct()

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries__in=value).distinct()

    def filter_crisis_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # internal filtering
                return qs.filter(crisis_type__in=value).distinct()
            # client side filtering
            return qs.filter(crisis_type__in=[
                Crisis.CRISIS_TYPE.get(item).value for item in value
            ]).distinct()
        return qs

    @property
    def qs(self):
        return super().qs.annotate(
            **Crisis._total_figure_disaggregation_subquery(),
        )
