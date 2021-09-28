import django_filters
from django.db.models import Q, Count
from apps.event.models import Actor, Event
from apps.crisis.models import Crisis
from apps.report.models import Report
from utils.filters import NameFilterMixin, StringListFilter, IDListFilter
from apps.event.constants import OSV


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
    created_by_ids = IDListFilter(method='filter_created_by')

    class Meta:
        model = Event
        fields = {
            'created_at': ['lte', 'lt', 'gte', 'gt'],
            'start_date': ['lte', 'lt', 'gte', 'gt'],
            'end_date': ['lte', 'lt', 'gte', 'gt'],
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

    @property
    def qs(self):
        return super().qs.annotate(
            **Event._total_figure_disaggregation_subquery(),
            entry_count=Count("entries"),
        ).prefetch_related("entries")

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
