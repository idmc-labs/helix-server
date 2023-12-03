import django_filters

from apps.crisis.models import Crisis
from apps.report.models import Report
from utils.filters import StringListFilter, NameFilterMixin, IDListFilter
from django.db.models import Q, Count


class CrisisFilter(NameFilterMixin, django_filters.FilterSet):
    name = django_filters.CharFilter(method='filter_name')
    countries = StringListFilter(method='filter_countries')
    crisis_types = StringListFilter(method='filter_crisis_types')
    events = IDListFilter(method='filter_events')

    # used in report crisis table
    report_id = django_filters.CharFilter(method='noop')
    created_by_ids = IDListFilter(method='filter_created_by')

    class Meta:
        model = Crisis
        fields = {
            'created_at': ['lt', 'lte', 'gt', 'gte'],
            'start_date': ['lt', 'lte', 'gt', 'gte'],
            'end_date': ['lt', 'lte', 'gt', 'gte'],
        }

    def noop(self, qs, name, value):
        return qs

    def filter_events(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(events__in=value).distinct()

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries__in=value).distinct()

    def filter_crisis_types(self, qs, name, value):
        if not value:
            return qs
        if isinstance(value[0], int):
            # internal filtering
            return qs.filter(crisis_type__in=value).distinct()
        # client side filtering
        return qs.filter(crisis_type__in=[
            Crisis.CRISIS_TYPE.get(item).value for item in value
        ]).distinct()

    def filter_name(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(Q(name__unaccent__icontains=value) | Q(events__name__unaccent__icontains=value)).distinct()

    def filter_created_by(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(created_by__in=value)

    @property
    def qs(self):
        qs = super().qs
        report_id = self.data.get('report_id')
        figure_qs = None
        reference_date = None
        if report_id:
            # TODO: Handle when report is None
            report = Report.objects.filter(id=report_id).first()
            figure_qs = report.report_figures
            reference_date = report.filter_figure_end_before
            qs = qs.filter(id__in=figure_qs.values('event__crisis'))
        return qs.annotate(
            **Crisis._total_figure_disaggregation_subquery(figures=figure_qs, reference_date=reference_date),
            **Crisis.annotate_review_figures_count(),
            event_count=Count('events'),
        ).prefetch_related('events').distinct()
