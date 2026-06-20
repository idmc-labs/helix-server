from django.contrib.postgres.aggregates.general import StringAgg
from django.db.models import (
    Exists,
    OuterRef,
    Q,
)
from django.db.models.sql.constants import LOUTER
from django_cte import With
from django_filters import rest_framework as df

from apps.common.enums import GENDER_TYPE
from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR
from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.entry.constants import FLOW, STOCK
from apps.entry.filters import FigureTagFilter
from apps.entry.models import (
    Entry,
    Figure,
    FigureTag,
)
from apps.event.constants import OSV
from apps.event.models import ContextOfViolence
from apps.extraction.models import ExtractionQuery
from apps.organization.models import Organization
from apps.report.models import Report
from utils.filters import (
    IDFilter,
    IDListFilter,
    MultiWordSearchFilterSet,
    StringListFilter,
    generate_type_for_filter_set,
)

MALE = GENDER_TYPE.MALE.name
FEMALE = GENDER_TYPE.FEMALE.name


class EntryExtractionFilterSet(MultiWordSearchFilterSet):
    # NOTE: these filter names exactly match the extraction query model field names
    filter_figure_events = IDListFilter(method="filter_figure_events_")

    filter_figure_crises = IDListFilter(method="filter_crises")

    filter_figure_sources = IDListFilter(method="filter_sources")
    filter_entry_publishers = IDListFilter(method="filter_publishers")
    filter_entry_article_title = df.CharFilter(method="multi_word_search")
    # NOTE: We want the multi_word_search to be filter_entry_article_title not search.
    search = None
    filter_figure_created_by = IDListFilter(method="filter_created_by")

    filter_figure_regions = IDListFilter(method="filter_regions")
    filter_figure_geographical_groups = IDListFilter(method="filter_geographical_groups")
    filter_figure_countries = IDListFilter(method="filter_countries")
    filter_figure_category_types = StringListFilter(method="filter_filter_figure_category_types")
    filter_figure_categories = StringListFilter(method="filter_filter_figure_categories")
    filter_figure_start_after = df.DateFilter(method="filter_time_frame_after")
    filter_figure_end_before = df.DateFilter(method="filter_time_frame_before")
    filter_figure_roles = StringListFilter(method="filter_filter_figure_roles")
    filter_figure_tags = IDListFilter(method="filter_tags")
    filter_figure_terms = IDListFilter(method="filter_by_figure_terms")
    filter_figure_crisis_types = StringListFilter(method="filter_crisis_types")
    filter_figure_disaster_categories = IDListFilter(method="filter_filter_figure_disaster_categories")
    filter_figure_disaster_sub_categories = IDListFilter(method="filter_filter_figure_disaster_sub_categories")
    filter_figure_disaster_sub_types = IDListFilter(method="filter_filter_figure_disaster_sub_types")
    filter_figure_disaster_types = IDListFilter(method="filter_filter_figure_disaster_types")
    filter_figure_violence_sub_types = IDListFilter(method="filter_filter_figure_violence_sub_types")
    filter_figure_violence_types = IDListFilter(method="filter_filter_figure_violence_types")
    filter_figure_osv_sub_types = IDListFilter(method="filter_filter_figure_osv_sub_types")
    filter_figure_review_status = StringListFilter(method="filter_filter_figure_review_status")
    filter_figure_has_disaggregated_data = df.BooleanFilter(method="filter_has_disaggregated_data")
    filter_figure_approved_by = IDListFilter(method="filter_filter_figure_approved_by")
    filter_figure_has_excerpt_idu = df.BooleanFilter(method="filter_filter_figure_has_excerpt_idu")
    filter_figure_has_housing_destruction = df.BooleanFilter(method="filter_filter_figure_has_housing_destruction")
    # used in report entry table
    report_id = IDFilter(method="filter_report")
    filter_figure_context_of_violence = IDListFilter(method="filter_filter_figure_context_of_violence")
    filter_figure_is_to_be_reviewed = df.BooleanFilter(method="filter_filter_figure_is_to_be_reviewed")

    class Meta:
        model = Entry
        fields = {}
        multi_word_search_fields = ["article_title"]

    @staticmethod
    def _figures_for_entry(**lookups):
        return Figure.objects.filter(entry=OuterRef("pk"), **lookups)

    def filter_created_by(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(Exists(self._figures_for_entry(created_by__in=value)))

    def filter_report(self, qs, name, value):
        if not value:
            return qs
        # report_figures is a property on Report that builds a filtered Figure
        # queryset from the report's stored filter kwargs — the .get() can't
        # be avoided, but the outer lookup is Exists for consistency.
        report = Report.objects.get(id=value)
        return qs.filter(Exists(report.report_figures.filter(entry=OuterRef("pk"))))

    def filter_geographical_groups(self, qs, name, value):
        if value:
            qs = qs.filter(Exists(self._figures_for_entry(country__geographical_group__in=value)))
        return qs

    def filter_regions(self, qs, name, value):
        if value:
            qs = qs.filter(Exists(self._figures_for_entry(country__region__in=value)))
        return qs

    def filter_countries(self, qs, name, value):
        if value:
            return qs.filter(Exists(self._figures_for_entry(country__in=value)))
        return qs

    def filter_figure_events_(self, qs, name, value):
        if value:
            return qs.filter(Exists(self._figures_for_entry(event__in=value)))
        return qs

    def filter_crises(self, qs, name, value):
        if value:
            return qs.filter(Exists(self._figures_for_entry(event__crisis__in=value)))
        return qs

    def filter_sources(self, qs, name, value):
        if value:
            return qs.filter(Exists(self._figures_for_entry(sources__in=value)))
        return qs

    def filter_publishers(self, qs, name, value):
        if value:
            return qs.filter(Exists(Organization.objects.filter(pk__in=value, published_entries=OuterRef("pk"))))
        return qs

    def filter_by_figure_terms(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(Exists(self._figures_for_entry(term__in=value)))
            return qs.filter(
                Exists(
                    self._figures_for_entry(
                        term__in=[Figure.FIGURE_TERMS.get(item).value for item in value],
                    )
                )
            )
        return qs

    def filter_filter_figure_category_types(self, qs, name, value):
        if not value:
            return qs
        # NOTE: category type is saved as 'Stock' and 'Flow' on database
        # so, using capitalize on enum values 'STOCK' and 'FLOW'
        category_enums_to_filter = []
        for category_type in value:
            if category_type == STOCK:
                category_enums_to_filter += Figure.stock_list()
            if category_type == FLOW:
                category_enums_to_filter += Figure.flow_list()
        return qs.filter(Exists(self._figures_for_entry(category__in=category_enums_to_filter)))

    def filter_filter_figure_categories(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(Exists(self._figures_for_entry(category__in=value)))
            return qs.filter(
                Exists(
                    self._figures_for_entry(
                        category__in=[Figure.FIGURE_CATEGORY_TYPES.get(item).value for item in value],
                    )
                )
            )
        return qs

    def filter_time_frame_after(self, qs, name, value):
        if value:
            return qs.filter(
                Exists(self._figures_for_entry().exclude(start_date__isnull=True).filter(start_date__gte=value))
            )
        return qs

    def filter_time_frame_before(self, qs, name, value):
        if value:
            return qs.filter(Exists(self._figures_for_entry().exclude(end_date__isnull=True).filter(end_date__lt=value)))
        return qs

    def filter_filter_figure_roles(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(Exists(self._figures_for_entry(role__in=value)))
            return qs.filter(
                Exists(
                    self._figures_for_entry(
                        role__in=[Figure.ROLE.get(item).value for item in value],
                    )
                )
            )
        return qs

    def filter_tags(self, qs, name, value):
        if value:
            return qs.filter(Exists(self._figures_for_entry(tags__in=value)))
        return qs

    def filter_crisis_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(Exists(self._figures_for_entry(figure_cause__in=value)))
            # coming from client side
            return qs.filter(
                Exists(
                    self._figures_for_entry(
                        figure_cause__in=[Crisis.CRISIS_TYPE.get(item).value for item in value],
                    )
                )
            )
        return qs

    def filter_filter_figure_disaster_categories(self, qs, name, value):
        if value:
            return qs.filter(
                Exists(
                    self._figures_for_entry().filter(
                        ~Q(figure_cause=Crisis.CRISIS_TYPE.DISASTER.value) | Q(disaster_category__in=value)
                    )
                )
            )
        return qs

    def filter_filter_figure_disaster_sub_categories(self, qs, name, value):
        if value:
            return qs.filter(
                Exists(
                    self._figures_for_entry().filter(
                        ~Q(figure_cause=Crisis.CRISIS_TYPE.DISASTER.value) | Q(disaster_sub_category__in=value)
                    )
                )
            )
        return qs

    def filter_filter_figure_disaster_sub_types(self, qs, name, value):
        if value:
            return qs.filter(
                Exists(
                    self._figures_for_entry().filter(
                        ~Q(figure_cause=Crisis.CRISIS_TYPE.DISASTER.value) | Q(disaster_sub_type__in=value)
                    )
                )
            )
        return qs

    def filter_filter_figure_disaster_types(self, qs, name, value):
        if value:
            return qs.filter(
                Exists(
                    self._figures_for_entry().filter(
                        ~Q(figure_cause=Crisis.CRISIS_TYPE.DISASTER.value) | Q(disaster_type__in=value)
                    )
                )
            )
        return qs

    def filter_filter_figure_violence_sub_types(self, qs, name, value):
        if value:
            return qs.filter(
                Exists(
                    self._figures_for_entry().filter(
                        ~Q(figure_cause=Crisis.CRISIS_TYPE.CONFLICT.value) | Q(violence_sub_type__in=value)
                    )
                )
            )
        return qs

    def filter_filter_figure_violence_types(self, qs, name, value):
        if value:
            return qs.filter(
                Exists(
                    self._figures_for_entry().filter(
                        ~Q(figure_cause=Crisis.CRISIS_TYPE.CONFLICT.value) | Q(violence_type__in=value)
                    )
                )
            )
        return qs

    def filter_filter_figure_osv_sub_types(self, qs, name, value):
        if value:
            return qs.filter(
                Exists(self._figures_for_entry().filter(~Q(event__violence__name=OSV) | Q(osv_sub_type__in=value)))
            )
        return qs

    def filter_has_disaggregated_data(self, qs, name, value):
        if value is True:
            return qs.filter(Exists(self._figures_for_entry(is_disaggregated=True)))
        if value is False:
            return qs.filter(Exists(self._figures_for_entry(is_disaggregated=False)))
        return qs

    def filter_filter_figure_context_of_violence(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(Exists(self._figures_for_entry(context_of_violence__in=value)))

    def filter_filter_figure_review_status(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                return qs.filter(Exists(self._figures_for_entry(review_status__in=value)))
            return qs.filter(
                Exists(
                    self._figures_for_entry(
                        review_status__in=[Figure.FIGURE_REVIEW_STATUS.get(item).value for item in value],
                    )
                )
            )
        return qs

    def filter_filter_figure_approved_by(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(Exists(self._figures_for_entry(approved_by__in=value)))

    def filter_filter_figure_has_excerpt_idu(self, qs, name, value):
        if value is None:
            return qs
        return qs.filter(Exists(self._figures_for_entry(include_idu=value)))

    def filter_filter_figure_has_housing_destruction(self, qs, name, value):
        if value is None:
            return qs
        return qs.filter(Exists(self._figures_for_entry(is_housing_destruction=value)))

    def filter_filter_figure_is_to_be_reviewed(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            Exists(
                self._figures_for_entry().filter(
                    Q(role=Figure.ROLE.RECOMMENDED) | Q(event__include_triangulation_in_qa=True)
                )
            )
        )


class BaseFigureExtractionFilterSet(MultiWordSearchFilterSet):
    # Opt-in: DjangoPaginatedListObjectField uses this marker to decide whether
    # to forward the active ordering as a constructor arg, so subclasses can
    # gate expensive annotations on it.
    accepts_ordering = True

    # NOTE: these filter names exactly match the extraction query model field names
    filter_figure_regions = IDListFilter(method="filter_regions")
    filter_figure_geographical_groups = IDListFilter(method="filter_geographical_groups")
    filter_figure_countries = IDListFilter(method="filter_countries")
    filter_figure_events = IDListFilter(method="filter_figure_events_")
    filter_figure_crises = IDListFilter(method="filter_crises")
    filter_figure_sources = IDListFilter(method="filter_sources")
    filter_entry_publishers = IDListFilter(method="filter_publishers")
    filter_figure_category_types = StringListFilter(method="filter_filter_figure_category_types")
    filter_figure_categories = StringListFilter(method="filter_filter_figure_categories")
    filter_figure_start_after = df.DateFilter(method="filter_time_frame_after")
    filter_figure_end_before = df.DateFilter(method="filter_time_frame_before")
    filter_figure_roles = StringListFilter(method="filter_filter_figure_roles")
    filter_entry_article_title = df.CharFilter(method="multi_word_search")
    # NOTE: We want the multi_word_search to be filter_entry_article_title not search.
    search = None
    filter_figure_tags = IDListFilter(method="filter_tags")
    filter_figure_crisis_types = StringListFilter(method="filter_crisis_types")
    filter_figure_created_by = IDListFilter(method="filter_filter_figure_created_by")
    filter_figure_terms = IDListFilter(method="filter_by_figure_terms")
    filter_figure_disaster_categories = IDListFilter(method="filter_filter_figure_disaster_categories")
    filter_figure_disaster_sub_categories = IDListFilter(method="filter_filter_figure_disaster_sub_categories")
    filter_figure_disaster_sub_types = IDListFilter(method="filter_filter_figure_disaster_sub_types")
    filter_figure_disaster_types = IDListFilter(method="filter_filter_figure_disaster_types")
    filter_figure_violence_sub_types = IDListFilter(method="filter_filter_figure_violence_sub_types")
    filter_figure_violence_types = IDListFilter(method="filter_filter_figure_violence_types")
    filter_figure_osv_sub_types = IDListFilter(method="filter_filter_figure_osv_sub_types")
    filter_figure_has_disaggregated_data = df.BooleanFilter(method="filter_has_disaggregated_data")
    # used in report entry table
    report_id = IDFilter(method="filter_report")
    filter_figure_context_of_violence = IDListFilter(method="filter_filter_figure_context_of_violence")
    filter_figure_review_status = StringListFilter(method="filter_filter_figure_review_status")
    filter_figure_approved_by = IDListFilter(method="filter_filter_figure_approved_by")
    filter_figure_is_to_be_reviewed = df.BooleanFilter(method="filter_filter_figure_is_to_be_reviewed")
    filter_figure_has_excerpt_idu = df.BooleanFilter(method="filter_filter_figure_has_excerpt_idu")
    filter_figure_has_housing_destruction = df.BooleanFilter(method="filter_filter_figure_has_housing_destruction")
    filter_figure_entry = df.CharFilter(field_name="entry", lookup_expr="exact")

    class Meta:
        model = Figure
        fields = []
        multi_word_search_fields = ["entry__article_title"]

    def __init__(self, *args, ordering=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ordering = ordering
        self.ordering_fields = {field.lstrip("-") for field in ordering.split(",") if field} if ordering else set()

    def filter_filter_figure_created_by(self, qs, name, value):
        if value:
            return qs.filter(created_by__in=value)
        return qs

    def filter_time_frame_after(self, qs, name, value):
        if value:
            return qs.exclude(start_date__isnull=True).filter(start_date__gte=value)
        return qs

    def filter_time_frame_before(self, qs, name, value):
        if value:
            return qs.exclude(end_date__isnull=True).filter(end_date__lt=value)
        return qs

    def filter_report(self, qs, name, value):
        if not value:
            return qs

        report = Report.objects.get(id=value)
        return ReportFigureExtractionFilterSet(
            queryset=qs,
            data=report.get_filter_kwargs,
        ).qs

    def filter_geographical_groups(self, qs, name, value):
        if value:
            countries_qs = Country.objects.filter(geographical_group__in=value, pk=OuterRef("country_id"))
            qs = qs.filter(Exists(countries_qs))
        return qs

    def filter_regions(self, qs, name, value):
        if value:
            countries_qs = Country.objects.filter(region__in=value, pk=OuterRef("country_id"))
            qs = qs.filter(Exists(countries_qs))
        return qs

    def filter_countries(self, qs, name, value):
        if value:
            return qs.filter(country__in=value)
        return qs

    def filter_figure_events_(self, qs, name, value):
        if value:
            return qs.filter(event__in=value)
        return qs

    def filter_crises(self, qs, name, value):
        if value:
            return qs.filter(event__crisis__in=value)
        return qs

    def filter_sources(self, qs, name, value):
        if value:
            return qs.filter(Exists(Organization.objects.filter(pk__in=value, sourced_figures=OuterRef("pk"))))
        return qs

    def filter_publishers(self, qs, name, value):
        if value:
            return qs.filter(Exists(Organization.objects.filter(pk__in=value, published_entries=OuterRef("entry_id"))))
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
        return qs.filter(category__in=category_enums_to_filter)

    def filter_filter_figure_categories(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(category__in=value)
            return qs.filter(category__in=[Figure.FIGURE_CATEGORY_TYPES.get(item).value for item in value])
        return qs

    def filter_filter_figure_roles(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(role__in=value)
            else:
                # coming from client side
                return qs.filter(role__in=[Figure.ROLE.get(item).value for item in value])
        return qs

    def filter_tags(self, qs, name, value):
        if value:
            return qs.filter(Exists(FigureTag.objects.filter(pk__in=value, figure=OuterRef("pk"))))
        return qs

    def filter_crisis_types(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(figure_cause__in=value)
            else:
                # coming from client side
                return qs.filter(figure_cause__in=[Crisis.CRISIS_TYPE.get(item).value for item in value])
        return qs

    def filter_filter_figure_has_excerpt_idu(self, qs, name, value):
        if value is None:
            return qs
        return qs.filter(include_idu=value)

    def filter_filter_figure_has_housing_destruction(self, qs, name, value):
        if value is None:
            return qs
        return qs.filter(is_housing_destruction=value)

    def filter_by_figure_terms(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                # coming from saved query
                return qs.filter(term__in=value)
            return qs.filter(term__in=[Figure.FIGURE_TERMS.get(item).value for item in value])
        return qs

    def filter_filter_figure_disaster_categories(self, qs, name, value):
        if value:
            return qs.filter(~Q(figure_cause=Crisis.CRISIS_TYPE.DISASTER.value) | Q(disaster_category__in=value))
        return qs

    def filter_filter_figure_disaster_sub_categories(self, qs, name, value):
        if value:
            return qs.filter(~Q(figure_cause=Crisis.CRISIS_TYPE.DISASTER.value) | Q(disaster_sub_category__in=value))
        return qs

    def filter_filter_figure_disaster_sub_types(self, qs, name, value):
        if value:
            return qs.filter(~Q(figure_cause=Crisis.CRISIS_TYPE.DISASTER.value) | Q(disaster_sub_type__in=value))
        return qs

    def filter_filter_figure_disaster_types(self, qs, name, value):
        if value:
            return qs.filter(~Q(figure_cause=Crisis.CRISIS_TYPE.DISASTER.value) | Q(disaster_type__in=value))
        return qs

    def filter_filter_figure_violence_sub_types(self, qs, name, value):
        if value:
            return qs.filter(~Q(figure_cause=Crisis.CRISIS_TYPE.CONFLICT.value) | Q(violence_sub_type__in=value))
        return qs

    def filter_filter_figure_violence_types(self, qs, name, value):
        if value:
            return qs.filter(~Q(figure_cause=Crisis.CRISIS_TYPE.CONFLICT.value) | Q(violence_type__in=value))
        return qs

    def filter_filter_figure_osv_sub_types(self, qs, name, value):
        if value:
            return qs.filter(~Q(event__violence__name=OSV) | Q(osv_sub_type__in=value))
        return qs

    def filter_has_disaggregated_data(self, qs, name, value):
        if value is True:
            return qs.filter(is_disaggregated=True)
        if value is False:
            return qs.filter(is_disaggregated=False)
        return qs

    def filter_filter_figure_context_of_violence(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(Exists(ContextOfViolence.objects.filter(pk__in=value, figures=OuterRef("pk"))))

    def filter_filter_figure_review_status(self, qs, name, value):
        if value:
            if isinstance(value[0], int):
                return qs.filter(review_status__in=value)
            return qs.filter(review_status__in=[Figure.FIGURE_REVIEW_STATUS.get(item).value for item in value])
        return qs

    def filter_filter_figure_approved_by(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(approved_by__in=value)

    def filter_filter_figure_is_to_be_reviewed(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(Q(role=Figure.ROLE.RECOMMENDED) | Q(event__include_triangulation_in_qa=True))


class FigureExtractionFilterSet(BaseFigureExtractionFilterSet):
    """
    NOTE: Return queryset as it is, don't apply filter here,
    filter is handled in qs method
    """

    filter_figure_start_after = df.DateFilter(method="noop")
    filter_figure_end_before = df.DateFilter(method="noop")

    def noop(self, qs, *args):
        return qs

    @property
    def qs(self):
        queryset = super().qs

        start_date = self.data.get("filter_figure_start_after")
        end_date = self.data.get("filter_figure_end_before")

        if start_date or end_date:
            queryset = Figure.with_year_difference(queryset).filter(
                Figure.nd_figures_q_for_listing(start_date, end_date)
                | Figure.idp_figures_q_for_listing(start_date, end_date)
            )

        if self.ordering_fields:
            # NOTE: expensive annotation for geolocations.
            # Aggregate over the whole Figure table via a CTE, then LEFT JOIN. This
            # is the fast path for the (large) figure list, which is the only place
            # figure-field ordering is exposed. A per-row correlated subquery would
            # win on small filtered subsets but loses badly here (186k per-row execs
            # vs one hash aggregation), so the whole-table CTE is the right default.
            if "geolocations" in self.ordering_fields:
                cte = With(
                    Figure.objects.values("id").annotate(
                        geolocations=StringAgg("geo_locations__display_name", EXTERNAL_ARRAY_SEPARATOR)
                    )
                )
                queryset = (
                    cte.join(queryset, id=cte.col.id, _join_type=LOUTER)
                    .with_cte(cte)
                    .annotate(geolocations=cte.col.geolocations)
                )

            # NOTE: expensive annotation for ordering and filtering.
            # we can't use elif here as ordering params can be multiple; is it practical?
            if "sources_reliability" in self.ordering_fields:
                cte = With(Figure.objects.values("id").annotate(**Figure.annotate_sources_reliability()))
                queryset = (
                    cte.join(queryset, id=cte.col.id, _join_type=LOUTER)
                    .with_cte(cte)
                    .annotate(sources_reliability=cte.col.sources_reliability)
                )

            stock_and_flow_annotations = {
                key: value for key, value in Figure.annotate_stock_and_flow_dates().items() if key in self.ordering_fields
            }
            if stock_and_flow_annotations:
                queryset = queryset.annotate(**stock_and_flow_annotations)

        return queryset


class ReportFigureExtractionFilterSet(BaseFigureExtractionFilterSet):
    """
    NOTE: Return queryset as it is, don't apply filter here,
    filter is handled in qs method

    NOTE: In report figures we have to pass end date as reference point
    """

    filter_figure_start_after = df.DateFilter(method="noop")
    filter_figure_end_before = df.DateFilter(method="noop")

    def noop(self, qs, *args):
        return qs

    @property
    def qs(self):
        queryset = super().qs
        start_date = self.data.get("filter_figure_start_after")
        end_date = self.data.get("filter_figure_end_before")

        return Figure.with_year_difference(queryset).filter(
            Figure.nd_figures_q_for_listing(start_date, end_date) | Figure.idp_figures_q_for_listing(start_date, end_date)
        )


class FigureExtractionBulkOperationFilterSet(ReportFigureExtractionFilterSet):
    filter_figure_ids = IDListFilter(method="filter_ids")
    filter_figure_exclude_ids = IDListFilter(method="filter_exclude_ids")

    def filter_ids(self, qs, _, value):
        if value:
            return qs.filter(id__in=value)
        return qs

    def filter_exclude_ids(self, qs, _, value):
        if value:
            return qs.exclude(id__in=value)
        return qs


class ExtractionQueryFilter(MultiWordSearchFilterSet):
    id = IDFilter(field_name="id", lookup_expr="exact")

    class Meta:
        model = ExtractionQuery
        fields = []
        multi_word_search_fields = ["name"]

    @property
    def qs(self):
        if self.request.user.is_authenticated:
            return super().qs.filter(created_by=self.request.user)
        return ExtractionQuery.objects.none()


FigureExtractionFilterDataType, FigureExtractionFilterDataInputType = generate_type_for_filter_set(
    FigureExtractionFilterSet,
    "entry.schema.figure_list",
    "FigureExtractionFilterDataType",
    "FigureExtractionFilterDataInputType",
)

EntryExtractionFilterDataType, EntryExtractionFilterDataInputType = generate_type_for_filter_set(
    EntryExtractionFilterSet,
    "entry.schema.entry_list",
    "EntryExtractionFilterDataType",
    "EntryExtractionFilterDataInputType",
)


FigureExtractionBulkOperationFilterDataType, FigureExtractionBulkOperationFilterDataInputType = generate_type_for_filter_set(
    FigureExtractionBulkOperationFilterSet,
    "entry.schema.figure_list",
    "FigureExtractionBulkOperationFilterDataType",
    "FigureExtractionBulkOperationFilterDataInputType",
)


FigureTagFilterDataType, FigureTagFilterDataInputType = generate_type_for_filter_set(
    FigureTagFilter,
    "entry.schema.figure_tag_list",
    "FigureTagFilterDataType",
    "FigureTagFilterDataInputType",
)
