import django_filters

from apps.crisis.models import Crisis
from apps.report.models import Report
from utils.filters import StringListFilter, NameFilterMixin, IDListFilter
from django.db.models import Q, Count
from apps.entry.models import EntryReviewer
from django.db import models


class CrisisFilter(NameFilterMixin, django_filters.FilterSet):
    name = django_filters.CharFilter(method='filter_name')
    countries = StringListFilter(method='filter_countries')
    crisis_types = StringListFilter(method='filter_crisis_types')
    events = IDListFilter(method='filter_events')

    # used in report crisis table
    report = django_filters.CharFilter(method='filter_report')
    created_by_ids = IDListFilter(method='filter_created_by')

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
        if not value:
            return qs
        if isinstance(value[0], int):
            # internal filtering
            return qs.filter(crisis_type__in=value).distinct()
        # client side filtering
        return qs.filter(crisis_type__in=[
            Crisis.CRISIS_TYPE.get(item).value for item in value
        ]).distinct()

    def filter_report(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            id__in=Report.objects.get(id=value).report_figures.values('event__crisis')
        )

    def filter_name(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(Q(name__unaccent__icontains=value) | Q(events__name__unaccent__icontains=value)).distinct()

    def filter_created_by(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(events__created_by__in=value)

    @property
    def qs(self):
        from apps.entry.models import Figure
        return super().qs.annotate(
            # **Crisis._total_figure_disaggregation_subquery(),
            event_count=Count('events'),
            total=models.Subquery(
                Figure.objects.filter(
                    event__crisis=models.OuterRef('pk')
                ).order_by().values('entry').annotate(
                    count=models.Count('entry__reviewing', distinct=True)
                ).values('count')[:1],
                output_field=models.IntegerField()
            ),
            total_signed_off=models.Subquery(
                Figure.objects.filter(
                    event__crisis=models.OuterRef('pk'),
                    entry__reviewing__status=EntryReviewer.REVIEW_STATUS.SIGNED_OFF,
                ).order_by().values('entry').annotate(
                    count=models.Count('entry__reviewing', distinct=True)
                ).values('count')[:1],
                output_field=models.IntegerField()
            ),
            total_review_completed=models.Subquery(
                Figure.objects.filter(
                    event__crisis=models.OuterRef('pk'),
                    entry__reviewing__status=EntryReviewer.REVIEW_STATUS.REVIEW_COMPLETED,
                ).order_by().values('entry').annotate(
                    count=models.Count('entry__reviewing', distinct=True)
                ).values('count')[:1],
                output_field=models.IntegerField()
            ),
            progress=models.Case(
                models.When(total__gt=0, then=(
                    models.F('total_signed_off') + models.F('total_review_completed')) / models.F('total')
                ),
                default=None,
                output_field=models.FloatField()
            )
        ).prefetch_related('events').distinct()
