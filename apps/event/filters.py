import django_filters
from django.db.models import Q, Count
from apps.event.models import Actor, Event, Figure
from apps.crisis.models import Crisis
from apps.report.models import Report
from utils.filters import NameFilterMixin, StringListFilter, IDListFilter
from apps.event.constants import OSV
from apps.entry.models import EntryReviewer, FigureCategory
from django.db import models
from apps.common.enums import QA_RECOMMENDED_FIGURE_TYPE


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
            id__in=Report.objects.get(id=value).report_figures.values('entry__event')
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
        return qs.filter(name__unaccent__icontains=value).distinct()

    def filter_osv_sub_types(self, qs, name, value):
        if value:
            return qs.filter(~Q(violence__name=OSV) | Q(osv_sub_type__in=value)).distinct()
        return qs

    def filter_qa_rules(self, qs, name, value):
        flow_qs = Event.objects.none()
        stock_qs = Event.objects.none()
        recommended_stock_figures_count = Count('entries__figures', filter=(
            Q(entries__figures__role=Figure.ROLE.RECOMMENDED) &
            Q(ignore_qa=False) &
            Q(entries__figures__category=FigureCategory.stock_idp_id()))
        )
        recommended_flow_figures_count = Count('entries__figures', filter=(
            Q(entries__figures__role=Figure.ROLE.RECOMMENDED) &
            Q(ignore_qa=False) &
            Q(entries__figures__category=FigureCategory.flow_new_displacement_id()))
        )
        annotated_fields = {
            'stock_figure_count': recommended_stock_figures_count,
            'flow_figure_count': recommended_flow_figures_count
        }
        if QA_RECOMMENDED_FIGURE_TYPE.HAS_NO_RECOMMENDED_FIGURES.name in value:
            flow_qs = qs.annotate(**annotated_fields).filter(
                ignore_qa=False,
                stock_figure_count=0, flow_figure_count=0
            )
        if QA_RECOMMENDED_FIGURE_TYPE.HAS_MULTIPLE_RECOMMENDED_FIGURES.name in value:
            stock_qs = qs.annotate(**annotated_fields).filter(
                ignore_qa=False,
                entries__figures__role=Figure.ROLE.RECOMMENDED
            ).filter(
                Q(stock_figure_count__gt=1) | Q(flow_figure_count__gt=1)
            )
        qs = flow_qs | stock_qs
        return qs.distinct()

    @property
    def qs(self):
        return super().qs.annotate(
            **Event._total_figure_disaggregation_subquery(),
            entry_count=Count("entries"),
            total=models.Count('entries__reviewing'),
            total_signed_off=models.Count(
                'entries__reviewing',
                filter=Q(entries__reviewing__status=EntryReviewer.REVIEW_STATUS.SIGNED_OFF),
                distinct=True
            ),
            total_review_completed=models.Count(
                'entries__reviewing', filter=Q(
                    entries__reviewing__status=EntryReviewer.REVIEW_STATUS.REVIEW_COMPLETED
                ),
                distinct=True
            ),
            progress=models.Case(
                models.When(total__gt=0, then=(
                    models.F('total_signed_off') + models.F('total_review_completed')) / models.F('total')
                ),
                default=None,
                output_field=models.FloatField()
            )
        ).prefetch_related("entries", "entries__reviewing", "entries__figures")

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
