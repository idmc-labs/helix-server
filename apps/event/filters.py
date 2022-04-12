import django_filters
from django.db.models import Q, Count
from apps.event.models import Actor, Event, Figure
from apps.crisis.models import Crisis
from apps.report.models import Report
from utils.filters import NameFilterMixin, StringListFilter, IDListFilter
from apps.event.constants import OSV
from apps.entry.models import EntryReviewer
from django.db import models
from apps.common.enums import QA_RULE_TYPE


class EventFilter(NameFilterMixin,
                  django_filters.FilterSet):
    name = django_filters.CharFilter(method='filter_name')
    crisis_by_ids = IDListFilter(method='filter_crises')
    event_types = StringListFilter(method='filter_event_types')
    countries = IDListFilter(method='filter_countries')
    glide_numbers = StringListFilter(method='filter_glide_numbers')

    osv_sub_type_by_ids = IDListFilter(method='filter_osv_sub_types')
    # used in report entry table
    report = django_filters.CharFilter(method='filter_report')
    disaster_sub_types = IDListFilter(method='filter_disaster_sub_types')
    violence_types = IDListFilter(method='filter_violence_types')
    violence_sub_types = IDListFilter(method='filter_violence_sub_types')
    created_by_ids = IDListFilter(method='filter_created_by')
    qa_rules = StringListFilter(method='filter_qa_rules')

    class Meta:
        model = Event
        fields = {
            'created_at': ['lte', 'lt', 'gte', 'gt'],
            'start_date': ['lte', 'lt', 'gte', 'gt'],
            'end_date': ['lte', 'lt', 'gte', 'gt'],
            'ignore_qa': ['exact']
        }

    def filter_report(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            id__in=Report.objects.get(id=value).report_figures.values('event')
        )

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries__in=value).distinct()

    def filter_disaster_sub_types(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(~Q(event_type=Crisis.CRISIS_TYPE.DISASTER.value) | Q(disaster_sub_type__in=value)).distinct()

    def filter_violence_types(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(~Q(event_type=Crisis.CRISIS_TYPE.CONFLICT.value) | Q(violence__in=value)).distinct()

    def filter_violence_sub_types(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(~Q(event_type=Crisis.CRISIS_TYPE.CONFLICT.value) | Q(violence_sub_type__in=value)).distinct()

    def filter_crises(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(crisis__in=value).distinct()

    def filter_event_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # internal filtering
                return qs.filter(event_type__in=value).distinct()
            return qs.filter(event_type__in=[
                Crisis.CRISIS_TYPE.get(item).value for item in value
            ]).distinct()
        return qs

    def filter_glide_numbers(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(glide_numbers__overlap=value).distinct()

    def filter_name(self, qs, name, value):
        if not value:
            return qs
        # NOTE: glide_numbers is arrayfield we have to pass List of string to filter
        return qs.filter(Q(name__unaccent__icontains=value) | Q(glide_numbers__overlap=[value])).distinct()

    def filter_osv_sub_types(self, qs, name, value):
        if value:
            return qs.filter(~Q(violence__name=OSV) | Q(osv_sub_type__in=value)).distinct()
        return qs

    def filter_qa_rules(self, qs, name, value):
        flow_qs_ids = []
        stock_qs_ids = []
        recommended_stock_figures_count = Count('figures', filter=(
            Q(figures__role=Figure.ROLE.RECOMMENDED) &
            Q(ignore_qa=False) &
            Q(entries__figures__category=Figure.FIGURE_CATEGORY_TYPES.IDPS))
        )
        recommended_flow_figures_count = Count('figures', filter=(
            Q(figures__role=Figure.ROLE.RECOMMENDED) &
            Q(ignore_qa=False) &
            Q(entries__figures__category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT))
        )
        annotated_fields = {
            'stock_figure_count': recommended_stock_figures_count,
            'flow_figure_count': recommended_flow_figures_count
        }
        if QA_RULE_TYPE.HAS_NO_RECOMMENDED_FIGURES.name in value:
            flow_qs_ids = qs.annotate(**annotated_fields).filter(
                ignore_qa=False,
                stock_figure_count=0, flow_figure_count=0
            ).values_list("id", flat=True)
        if QA_RULE_TYPE.HAS_MULTIPLE_RECOMMENDED_FIGURES.name in value:
            stock_qs_ids = qs.annotate(**annotated_fields).filter(
                ignore_qa=False,
                figures__role=Figure.ROLE.RECOMMENDED
            ).filter(
                Q(stock_figure_count__gt=1) | Q(flow_figure_count__gt=1)
            ).values_list("id", flat=True)
        event_ids = list(flow_qs_ids) + list(stock_qs_ids)
        return qs.filter(id__in=event_ids)

    @property
    def qs(self):
        return super().qs.annotate(
            **Event._total_figure_disaggregation_subquery(),
            entry_count=models.Subquery(
                Figure.objects.filter(
                    event=models.OuterRef('pk')
                ).order_by().values('entry').annotate(
                    count=models.Count('entry', distinct=True)
                ).values('count')[:1],
                output_field=models.IntegerField()
            ),
            total=models.Subquery(
                Figure.objects.filter(
                    event=models.OuterRef('pk')
                ).order_by().values('entry').annotate(
                    count=models.Count('entry__reviewing', distinct=True)
                ).values('count')[:1],
                output_field=models.IntegerField()
            ),
            total_signed_off=models.Subquery(
                Figure.objects.filter(
                    event=models.OuterRef('pk'),
                    entry__reviewing__status=EntryReviewer.REVIEW_STATUS.SIGNED_OFF,
                ).order_by().values('entry').annotate(
                    count=models.Count('entry__reviewing', distinct=True)
                ).values('count')[:1],
                output_field=models.IntegerField()
            ),
            total_review_completed=models.Subquery(
                Figure.objects.filter(
                    event=models.OuterRef('pk'),
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
        ).prefetch_related("figures")

    def filter_created_by(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(created_by__in=value)


class ActorFilter(django_filters.FilterSet):
    class Meta:
        model = Actor
        fields = {
            'name': ['unaccent__icontains']
        }
