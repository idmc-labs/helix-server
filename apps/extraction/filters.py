from django_filters import rest_framework as df
from django.db.models import Q
from django.utils import timezone
from apps.crisis.models import Crisis
from apps.country.models import Country
from apps.extraction.models import ExtractionQuery
from apps.entry.models import (
    Entry,
    Figure,
    EntryReviewer,
    FigureDisaggregationAbstractModel,
)
from apps.report.models import Report
from utils.filters import StringListFilter, IDListFilter
from apps.event.constants import OSV
from apps.common.enums import GENDER_TYPE
from apps.entry.constants import STOCK, FLOW

RURAL = FigureDisaggregationAbstractModel.DISPLACEMENT_TYPE.RURAL.name
URBAN = FigureDisaggregationAbstractModel.DISPLACEMENT_TYPE.URBAN.name
MALE = GENDER_TYPE.MALE.name
FEMALE = GENDER_TYPE.FEMALE.name


class EntryExtractionFilterSet(df.FilterSet):
    # NOTE: these filter names exactly match the extraction query model field names
    filter_figure_regions = IDListFilter(method='filter_regions')
    filter_figure_geographical_groups = IDListFilter(method='filter_geographical_groups')
    filter_figure_countries = IDListFilter(method='filter_countries')
    filter_events = IDListFilter(method='filter_events_')
    filter_event_crises = IDListFilter(method='filter_crises')
    filter_entry_sources = IDListFilter(method='filter_sources')
    filter_entry_publishers = IDListFilter(method='filter_publishers')
    filter_figure_category_types = StringListFilter(method='filter_filter_figure_category_types')
    filter_figure_categories = StringListFilter(method='filter_filter_figure_categories')
    filter_figure_start_after = df.DateFilter(method='filter_time_frame_after')
    filter_figure_end_before = df.DateFilter(method='filter_time_frame_before')
    filter_figure_roles = StringListFilter(method='filter_filter_figure_roles')
    filter_figure_tags = IDListFilter(method='filter_tags')
    filter_entry_article_title = df.CharFilter(field_name='article_title', lookup_expr='unaccent__icontains')
    filter_event_glide_number = StringListFilter(method='filter_filter_event_glide_number')
    filter_event_crisis_types = StringListFilter(method='filter_crisis_types')
    filter_entry_review_status = StringListFilter(method='filter_by_review_status')
    filter_entry_created_by = IDListFilter(field_name='created_by', lookup_expr='in')
    filter_figure_displacement_types = StringListFilter(method='filter_by_figure_displacement_types')
    filter_figure_terms = IDListFilter(method='filter_by_figure_terms')
    filter_event_disaster_categories = IDListFilter(method='filter_filter_event_disaster_categories')
    filter_event_disaster_sub_categories = IDListFilter(method='filter_filter_event_disaster_sub_categories')
    filter_event_disaster_sub_types = IDListFilter(method='filter_filter_event_disaster_sub_types')
    filter_event_disaster_types = IDListFilter(method='filter_filter_event_disaster_types')
    filter_event_violence_sub_types = IDListFilter(method='filter_filter_event_violence_sub_types')
    filter_event_violence_types = IDListFilter(method='filter_filter_event_violence_types')
    filter_entry_has_review_comments = df.BooleanFilter(method='filter_has_review_comments', initial=False)
    filter_event_osv_sub_types = IDListFilter(method='filter_filter_event_osv_sub_types')
    filter_entry_has_disaggregated_data = df.BooleanFilter(method='filter_has_disaggregated_data', initial=False)
    # used in report entry table
    report = df.CharFilter(method='filter_report')

    class Meta:
        model = Entry
        fields = {
            'event': ['exact'],
        }

    def filter_report(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            id__in=Report.objects.get(id=value).report_figures.values('entry')
        )

    def filter_geographical_groups(self, qs, name, value):
        if value:
            qs = qs.filter(
                id__in=Figure.objects.filter(
                    country__geographical_group__in=value
                ).values('entry')
            )
        return qs

    def filter_regions(self, qs, name, value):
        if value:
            qs = qs.filter(
                id__in=Figure.objects.filter(
                    country__region__in=value
                ).values('entry')
            )
        return qs

    def filter_countries(self, qs, name, value):
        if value:
            return qs.filter(
                id__in=Figure.objects.filter(
                    country__in=value
                ).values('entry')
            )
        return qs

    def filter_events_(self, qs, name, value):
        if value:
            return qs.filter(event__in=value).distinct()
        return qs

    def filter_crises(self, qs, name, value):
        if value:
            return qs.filter(event__crisis__in=value).distinct()
        return qs

    def filter_sources(self, qs, name, value):
        if value:
            return qs.filter(sources__in=value).distinct()
        return qs

    def filter_publishers(self, qs, name, value):
        if value:
            return qs.filter(publishers__in=value).distinct()
        return qs

    def filter_by_figure_terms(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(figures__in=Figure.objects.filter(term__in=value))

            return qs.filter(figures__term__in=[
                Figure.FIGURE_TERMS.get(item).value for item in value
            ]).distinct()
        return qs

    def filter_filter_figure_category_types(self, qs, name, value):
        if not value:
            return qs
        # NOTE: category type is saved as 'Stock' and 'Flow' on database
        # so, using capitalize on enum values 'STOCK' and 'FLOW'
        category_enums_to_filter = []
        for category_type in value:
            if category_type == STOCK:
                category_enums_to_filter = category_enums_to_filter + Figure.stock_list()
            if category_type == FLOW:
                category_enums_to_filter = category_enums_to_filter + Figure.flow_list()
        return qs.filter(figures__category__in=category_enums_to_filter).distinct()

    def filter_filter_figure_categories(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(figures__category__in=value)
            return qs.filter(figures__category__in=[
                Figure.FIGURE_CATEGORY_TYPES.get(item).value for item in value
            ])
        return qs

    def filter_time_frame_after(self, qs, name, value):
        if value:
            return qs\
                .filter(
                    id__in=Figure.objects
                    .exclude(start_date__isnull=True)
                    .filter(start_date__gte=value)
                    .values('entry')
                )
        return qs

    def filter_time_frame_before(self, qs, name, value):
        if value:
            return qs\
                .filter(
                    id__in=Figure.objects
                    .exclude(end_date__isnull=True)
                    .filter(end_date__lt=value)
                    .values('entry')
                )
        return qs

    def filter_filter_figure_roles(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(id__in=Figure.objects.filter(role__in=value))
            return qs.filter(
                id__in=Figure.objects.filter(role__in=[
                    Figure.ROLE.get(item).value for item in value
                ]))
        return qs

    def filter_tags(self, qs, name, value):
        if value:
            return qs.filter(figures__tags__in=value).distinct()
        return qs

    def filter_crisis_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(event__event_type__in=value).distinct()
            # coming from client side
            return qs.filter(event__event_type__in=[
                Crisis.CRISIS_TYPE.get(item).value for item in value
            ])
        return qs

    def filter_by_review_status(self, qs, name, value):
        if not value:
            return qs
        to_be_reviewed_qs = Entry.objects.none()
        if EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED.name in value:
            value.remove(EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED.name)
            to_be_reviewed_qs = qs.filter(
                Q(review_status__isnull=True) | Q(review_status=EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED.value)
            )
        db_values = [EntryReviewer.REVIEW_STATUS.get(item) for item in value]
        qs = qs.filter(review_status__in=db_values) | to_be_reviewed_qs
        return qs.distinct()

    def filter_by_figure_displacement_types(self, qs, name, value):
        if not value:
            return qs

        query_expr = Q()
        if RURAL in value:
            query_expr = query_expr | Q(figures__disaggregation_displacement_rural__gt=0)
        if URBAN in value:
            query_expr = query_expr | Q(figures__disaggregation_displacement_urban__gt=0)
        return qs.filter(query_expr).distinct()

    def filter_filter_event_disaster_categories(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    event__event_type=Crisis.CRISIS_TYPE.DISASTER.value
                ) | Q(event__disaster_category__in=value)
            ).distinct()
        return qs

    def filter_filter_event_disaster_sub_categories(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    event__event_type=Crisis.CRISIS_TYPE.DISASTER.value
                ) | Q(event__disaster_sub_category__in=value)
            ).distinct()
        return qs

    def filter_filter_event_disaster_sub_types(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    event__event_type=Crisis.CRISIS_TYPE.DISASTER.value
                ) | Q(event__disaster_sub_type__in=value)
            ).distinct()
        return qs

    def filter_filter_event_disaster_types(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    event__event_type=Crisis.CRISIS_TYPE.DISASTER.value
                ) | Q(event__disaster_type__in=value)
            ).distinct()
        return qs

    def filter_filter_event_violence_sub_types(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    event__event_type=Crisis.CRISIS_TYPE.CONFLICT.value
                ) | Q(event__violence_sub_type__in=value)
            ).distinct()
        return qs

    def filter_filter_event_violence_types(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    event__event_type=Crisis.CRISIS_TYPE.CONFLICT.value
                ) | Q(event__violence_type__in=value)
            ).distinct()
        return qs

    def filter_has_review_comments(self, qs, name, value):
        if value is True:
            return qs.filter(review_comments__isnull=False)
        if value is False:
            return qs.filter(review_comments__isnull=True)
        return qs

    def filter_filter_event_glide_number(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(event__glide_numbers__overlap=value).distinct()

    def filter_filter_event_osv_sub_types(self, qs, name, value):
        if value:
            return qs.filter(~Q(event__violence__name=OSV) | Q(event__osv_sub_type__in=value)).distinct()
        return qs

    def filter_has_disaggregated_data(self, qs, name, value):
        if value is True:
            return qs.filter(figures__disaggregation_age__isnull=False)
        if value is False:
            return qs.filter(figures__disaggregation_age__isnull=True)
        return qs

    @property
    def qs(self):
        return super().qs.annotate(
            **Entry._total_figure_disaggregation_subquery(),
        ).prefetch_related('review_comments').distinct()


class BaseFigureExtractionFilterSet(df.FilterSet):
    # NOTE: these filter names exactly match the extraction query model field names
    filter_figure_regions = IDListFilter(method='filter_regions')
    filter_figure_geographical_groups = IDListFilter(method='filter_geographical_groups')
    filter_figure_countries = IDListFilter(method='filter_countries')
    filter_events = IDListFilter(method='filter_events_')
    filter_event_crises = IDListFilter(method='filter_crises')
    filter_entry_sources = IDListFilter(method='filter_sources')
    filter_entry_publishers = IDListFilter(method='filter_publishers')
    filter_figure_category_types = StringListFilter(method='filter_filter_figure_category_types')
    filter_figure_categories = StringListFilter(method='filter_filter_figure_categories')
    filter_figure_start_after = df.DateFilter(method='filter_time_frame_after')
    filter_figure_end_before = df.DateFilter(method='filter_time_frame_before')
    filter_figure_roles = StringListFilter(method='filter_filter_figure_roles')
    filter_entry_article_title = df.CharFilter(field_name='entry__article_title', lookup_expr='unaccent__icontains')
    filter_figure_tags = IDListFilter(method='filter_tags')
    filter_event_crisis_types = StringListFilter(method='filter_crisis_types')
    filter_event_glide_number = StringListFilter(method='filter_filter_event_glide_number')
    filter_entry_review_status = StringListFilter(method='filter_by_review_status')
    filter_entry_created_by = IDListFilter(field_name='entry__created_by', lookup_expr='in')
    filter_figure_displacement_types = StringListFilter(method='filter_by_figure_displacement_types')
    filter_figure_terms = IDListFilter(method='filter_by_figure_terms')
    event = df.CharFilter(field_name='entry__event', lookup_expr='exact')
    filter_event_disaster_categories = IDListFilter(method='filter_filter_event_disaster_categories')
    filter_event_disaster_sub_categories = IDListFilter(method='filter_filter_event_disaster_sub_categories')
    filter_event_disaster_sub_types = IDListFilter(method='filter_filter_event_disaster_sub_types')
    filter_event_disaster_types = IDListFilter(method='filter_filter_event_disaster_types')
    filter_event_violence_sub_types = IDListFilter(method='filter_filter_event_violence_sub_types')
    filter_event_violence_types = IDListFilter(method='filter_filter_event_violence_types')
    filter_entry_has_review_comments = df.BooleanFilter(method='filter_has_review_comments', initial=False)
    filter_event_osv_sub_types = IDListFilter(method='filter_filter_event_osv_sub_types')
    filter_entry_has_disaggregated_data = df.BooleanFilter(method='filter_has_disaggregated_data', initial=False)
    # used in report entry table
    report = df.CharFilter(method='filter_report')

    class Meta:
        model = Figure
        fields = ['entry']

    def filter_time_frame_after(self, qs, name, value):
        if value:
            return qs.exclude(start_date__isnull=True)\
                .filter(start_date__gte=value).distinct()
        return qs

    def filter_time_frame_before(self, qs, name, value):
        if value:
            return qs.exclude(end_date__isnull=True).\
                filter(end_date__lt=value).distinct()
        return qs

    def filter_report(self, qs, name, value):
        if not value:
            return qs

        return qs.filter(
            id__in=Report.objects.get(id=value).report_figures.values('id')
        )

    def filter_geographical_groups(self, qs, name, value):
        if value:
            qs = qs.filter(
                country__in=Country.objects.filter(
                    geographical_group__in=value
                )
            )
        return qs

    def filter_regions(self, qs, name, value):
        if value:
            qs = qs.filter(
                country__in=Country.objects.filter(
                    region__in=value
                )
            )
        return qs

    def filter_countries(self, qs, name, value):
        if value:
            return qs.filter(country__in=value).distinct()
        return qs

    def filter_events_(self, qs, name, value):
        if value:
            return qs.filter(entry__event__in=value).distinct()
        return qs

    def filter_crises(self, qs, name, value):
        if value:
            return qs.filter(entry__event__crisis__in=value).distinct()
        return qs

    def filter_sources(self, qs, name, value):
        if value:
            return qs.filter(entry__sources__in=value).distinct()
        return qs

    def filter_publishers(self, qs, name, value):
        if value:
            return qs.filter(entry__publishers__in=value).distinct()
        return qs

    def filter_filter_figure_category_types(self, qs, name, value):
        if not value:
            return qs
        # NOTE: category type is saved as 'Stock' and 'Flow' on database
        # so, using capitalize on enum values 'STOCK' and 'FLOW'
        category_enums_to_filter = []
        for category_type in value:
            if category_type == STOCK:
                category_enums_to_filter = category_enums_to_filter + Figure.stock_list()
            if category_type == FLOW:
                category_enums_to_filter = category_enums_to_filter + Figure.flow_list()
        return qs.filter(category__in=category_enums_to_filter).distinct()

    def filter_filter_figure_categories(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(category__in=value)
            return qs.filter(category__in=[
                Figure.FIGURE_CATEGORY_TYPES.get(item).value for item in value
            ])
        return qs

    def filter_filter_figure_roles(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(role__in=value)
            else:
                # coming from client side
                return qs.filter(
                    role__in=[Figure.ROLE.get(item).value for item in value]
                )
        return qs

    def filter_tags(self, qs, name, value):
        if value:
            return qs.filter(tags__in=value).distinct()
        return qs

    def filter_crisis_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(entry__event__event_type__in=value).distinct()
            else:
                # coming from client side
                return qs.filter(entry__event__event_type__in=[
                    Crisis.CRISIS_TYPE.get(item).value for item in value
                ])
        return qs

    def filter_by_review_status(self, qs, name, value):
        if not value:
            return qs
        to_be_reviewed_qs = Figure.objects.none()
        if EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED.name in value:
            value.remove(EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED.name)
            to_be_reviewed_qs = qs.filter(
                Q(entry__review_status__isnull=True) |
                Q(entry__review_status=EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED.value)
            )
        db_values = [EntryReviewer.REVIEW_STATUS.get(item) for item in value]
        qs = qs.filter(entry__review_status__in=db_values) | to_be_reviewed_qs
        return qs.distinct()

    def filter_by_figure_displacement_types(self, qs, name, value):
        if not value:
            return qs

        query_expr = Q()
        if RURAL in value:
            query_expr = query_expr | Q(disaggregation_displacement_rural__gt=0)
        if URBAN in value:
            query_expr = query_expr | Q(disaggregation_displacement_urban__gt=0)
        return qs.filter(query_expr)

    def filter_by_figure_terms(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(term__in=value)
            return qs.filter(term__in=[
                Figure.FIGURE_TERMS.get(item).value for item in value
            ])
        return qs

    def filter_filter_event_disaster_categories(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER.value
                ) | Q(entry__event__disaster_category__in=value)
            ).distinct()
        return qs

    def filter_filter_event_disaster_sub_categories(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER.value
                ) | Q(entry__event__disaster_sub_category__in=value)
            ).distinct()
        return qs

    def filter_filter_event_disaster_sub_types(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER.value
                ) | Q(entry__event__disaster_sub_type__in=value)
            ).distinct()
        return qs

    def filter_filter_event_disaster_types(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER.value
                ) | Q(entry__event__disaster_type__in=value)
            ).distinct()
        return qs

    def filter_filter_event_violence_sub_types(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    entry__event__event_type=Crisis.CRISIS_TYPE.CONFLICT.value
                ) | Q(entry__event__violence_sub_type__in=value)
            ).distinct()
        return qs

    def filter_filter_event_violence_types(self, qs, name, value):
        if value:
            return qs.filter(
                ~Q(
                    entry__event__event_type=Crisis.CRISIS_TYPE.CONFLICT.value
                ) | Q(entry__event__violence_type__in=value)
            ).distinct()
        return qs

    def filter_has_review_comments(self, qs, name, value):
        if value is True:
            return qs.filter(entry__review_comments__isnull=False)
        if value is False:
            return qs.filter(entry__review_comments__isnull=True)
        return qs

    def filter_filter_event_glide_number(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(entry__event__glide_numbers__overlap=value).distinct()

    def filter_filter_event_osv_sub_types(self, qs, name, value):
        if value:
            return qs.filter(~Q(entry__event__violence__name=OSV) | Q(entry__event__osv_sub_type__in=value)).distinct()
        return qs

    def filter_has_disaggregated_data(self, qs, name, value):
        if value is True:
            return qs.filter(disaggregation_age__isnull=False)
        if value is False:
            return qs.filter(disaggregation_age__isnull=True)
        return qs

    @property
    def qs(self):
        # FIXME: using this prefetch_related results in calling count after a
        # subquery. This has a severe performance penalty
        return super().qs.prefetch_related('entry__review_comments').distinct()


class FigureExtractionFilterSet(BaseFigureExtractionFilterSet):
    """
    NOTE: Return queryset as it is, don't apply filter here,
    filter is handled in qs method
    """
    filter_figure_start_after = df.DateFilter(method='noop')
    filter_figure_end_before = df.DateFilter(method='noop')

    def noop(self, qs, *args):
        return qs

    @property
    def qs(self):
        queryset = super().qs
        start_date = self.data.get('filter_figure_start_after')
        end_date = self.data.get('filter_figure_end_before')

        flow_qs = Figure.filtered_nd_figures(
            queryset, start_date, end_date
        )
        stock_qs = Figure.filtered_idp_figures(
            queryset, reference_point=timezone.now().date()
        )
        return flow_qs | stock_qs


class ReportFigureExtractionFilterSet(BaseFigureExtractionFilterSet):
    """
    NOTE: Return queryset as it is, don't apply filter here,
    filter is handled in qs method

    NOTE: In report figures we have to pass end date as reference pont
    """
    filter_figure_start_after = df.DateFilter(method='noop')
    filter_figure_end_before = df.DateFilter(method='noop')

    def noop(self, qs, *args):
        return qs

    @property
    def qs(self):
        queryset = super().qs
        start_date = self.data.get('filter_figure_start_after')
        end_date = self.data.get('filter_figure_end_before')

        flow_qs = Figure.filtered_nd_figures(
            queryset, start_date, end_date
        )
        stock_qs = Figure.filtered_idp_figures(
            queryset, reference_point=end_date
        )
        return flow_qs | stock_qs


class ExtractionQueryFilter(df.FilterSet):
    class Meta:
        model = ExtractionQuery
        fields = {
            'id': ('exact',),
            'name': ('unaccent__icontains',),
        }

    @property
    def qs(self):
        if self.request.user.is_authenticated:
            return super().qs.filter(created_by=self.request.user)
        return ExtractionQuery.objects.none()
