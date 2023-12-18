import django_filters
from django.db.models import Q, Count
from django.contrib.postgres.aggregates.general import ArrayAgg
from apps.event.models import (
    Actor,
    Event,
    Figure,
    DisasterSubType,
    DisasterType,
    DisasterCategory,
    DisasterSubCategory,
    ContextOfViolence,
    OsvSubType,
    OtherSubType,
)
from apps.crisis.models import Crisis
from apps.report.models import Report
from utils.filters import NameFilterMixin, StringListFilter, IDListFilter
from apps.event.constants import OSV
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
    qa_rule = django_filters.CharFilter(method='filter_qa_rule')
    context_of_violences = IDListFilter(method='filter_context_of_violences')
    review_status = StringListFilter(method='filter_review_status')
    assignees = IDListFilter(method='filter_assignees')
    assigners = IDListFilter(method='filter_assigners')

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

    def filter_review_status(self, qs, name, value):
        # Filter out *_BUT_CHANGED values from user input
        value = [
            v
            for v in value or []
            if v not in [
                Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED.value,
                Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED.name,
                Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED.value,
                Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED.name,
            ]
        ]
        if value:
            if (
                Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS.value in value or
                Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS.name in value
            ):
                # Add *_BUT_CHANGED values if REVIEW_IN_PROGRESS is provided by user
                value = [
                    *value,
                    Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED.value,
                    Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED.value,
                ]
            if isinstance(value[0], int):
                return qs.filter(review_status__in=value).distinct()
            return qs.filter(review_status__in=[
                # NOTE: item is string. eg: 'REVIEW_IN_PROGRESS'
                Event.EVENT_REVIEW_STATUS.get(item).value
                for item in value
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

    def filter_qa_rule(self, qs, name, value):
        if QA_RULE_TYPE.HAS_NO_RECOMMENDED_FIGURES.name == value:
            return qs.annotate(
                figure_count=Count(
                    'figures', filter=Q(
                        figures__category__in=[
                            Figure.FIGURE_CATEGORY_TYPES.IDPS,
                            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                        ],
                        ignore_qa=False,
                        figures__role=Figure.ROLE.RECOMMENDED,
                        figures__geo_locations__isnull=False,
                    )
                )
            ).filter(
                figure_count=0
            )
        elif QA_RULE_TYPE.HAS_MULTIPLE_RECOMMENDED_FIGURES.name == value:
            events_id_qs = Figure.objects.filter(
                category__in=[
                    Figure.FIGURE_CATEGORY_TYPES.IDPS,
                    Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                ],
                event__ignore_qa=False,
                role=Figure.ROLE.RECOMMENDED,
                geo_locations__isnull=False,
            ).annotate(
                locations=models.Subquery(
                    Figure.geo_locations.through.objects.filter(
                        figure=models.OuterRef('pk')
                    ).order_by().values('figure').annotate(
                        locations=ArrayAgg(
                            'osmname__name', distinct=True, ordering='osmname__name'
                        ),
                    ).values('locations')[:1],
                    output_field=models.CharField(),
                ),
            ).order_by().values('event', 'category', 'locations').annotate(
                count=Count('id', distinct=True),
            )
            return qs.filter(
                id__in=events_id_qs.filter(count__gt=1).values('event').distinct()
            )
        return qs

    def filter_context_of_violences(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(context_of_violence__in=value).distinct()

    def filter_assigners(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(assigner__in=value)

    def filter_assignees(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(assignee__in=value)

    @property
    def qs(self):
        return super().qs.annotate(
            **Event._total_figure_disaggregation_subquery(),
            **Event.annotate_review_figures_count(),
            entry_count=models.Subquery(
                Figure.objects.filter(
                    event=models.OuterRef('pk')
                ).order_by().values('event').annotate(
                    count=models.Count('entry', distinct=True)
                ).values('count')[:1],
                output_field=models.IntegerField()
            )
        ).prefetch_related("figures", 'context_of_violence')

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


class DisasterSubTypeFilter(django_filters.FilterSet):
    class Meta:
        model = DisasterSubType
        fields = {
            'name': ['unaccent__icontains']
        }


class DisasterTypeFilter(django_filters.FilterSet):
    class Meta:
        model = DisasterType
        fields = {
            'name': ['unaccent__icontains']
        }


class DisasterCategoryFilter(django_filters.FilterSet):
    class Meta:
        model = DisasterCategory
        fields = {
            'name': ['unaccent__icontains']
        }


class DisasterSubCategoryFilter(django_filters.FilterSet):
    class Meta:
        model = DisasterSubCategory
        fields = {
            'name': ['unaccent__icontains']
        }


class OsvSubTypeFilter(django_filters.FilterSet):
    class Meta:
        model = OsvSubType
        fields = {
            'name': ['icontains']
        }


class OtherSubTypeFilter(django_filters.FilterSet):
    class Meta:
        model = OtherSubType
        fields = {
            'name': ['icontains']
        }


class ContextOfViolenceFilter(django_filters.FilterSet):
    class Meta:
        model = ContextOfViolence
        fields = {
            'name': ['icontains']
        }
