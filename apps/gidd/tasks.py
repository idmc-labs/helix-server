import datetime
import logging

from django.contrib.postgres.aggregates.general import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db import connection, models, transaction
from django.db.models import (
    Case,
    F,
    Func,
    IntegerField,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Cast, Coalesce, Concat
from django.db.models.sql.constants import LOUTER
from django.utils import timezone
from django_cte import With

from apps.common.utils import EXTERNAL_TUPLE_SEPARATOR
from apps.country.models import Country
from apps.entry.models import Figure
from apps.event.models import Crisis, Event, EventCode
from apps.report.models import Report
from helix.celery import app as celery_app
from utils.common import redis_lock, round_and_remove_zero
from utils.db import Array, rounded_figure_expr

from .models import (
    GiddDisplacement,
    GiddEvent,
    GiddEventDisplacement,
    GiddFigure,
    IdpsSaddEstimate,
    PublicFigureAnalysis,
    StatusLog,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_gidd_years():
    return (
        Report.objects.filter(is_gidd_report=True)
        .order_by("gidd_report_year")
        .distinct("gidd_report_year")
        .values_list("gidd_report_year", flat=True)
    )


def empty_int_array():
    return Value([], output_field=ArrayField(models.IntegerField()))


def empty_char_array():
    # TextField base: a bare CharField renders an invalid `varchar(None)[]` cast.
    return Value([], output_field=ArrayField(models.TextField()))


def enum_label_case(field_name, enum_class):
    """DB-side `enum_label_text`: raw copies bypass the TextField str()
    coercion that rendered enum labels into text columns — CASE-map the
    label explicitly."""
    return Case(
        *[When(**{field_name: member}, then=Value(enum_label_text(member))) for member in enum_class],
        # An int outside the enum keeps its digits, as the TextField str() coercion on the previous
        # bulk_create path did. Without a default the CASE falls through to NULL, which would empty
        # a published column -- and, inside ArrayAgg, put a NULL element in the array.
        default=Cast(F(field_name), models.TextField()),
        output_field=models.TextField(),
    )


def figures_in_year_window(year, event_type=None):
    """The per-year GIDD window: flow figures via the Jan1-Dec31 start/end
    rules, stock figures counted at Dec 31 (`filtered_idp_figures` exact).

    FIXME: Check if this should be
    - Figure.filtered_nd_figures_for_listing
    - Figure.filtered_idp_figures_for_listing
    NOTE: No we do not need to use the listing method as we are aggregating
    """
    queryset = Figure.objects.filter(role=Figure.ROLE.RECOMMENDED)
    if event_type is not None:
        queryset = queryset.filter(event__event_type=event_type)
    nd_figure_qs = Figure.filtered_nd_figures(
        qs=queryset,
        start_date=datetime.datetime(year=year, month=1, day=1),
        end_date=datetime.datetime(year=year, month=12, day=31),
    )
    stock_figure_qs = Figure.filtered_idp_figures(
        qs=queryset,
        start_date=datetime.datetime(year=year, month=1, day=1),
        end_date=datetime.datetime(year=year, month=12, day=31),
    )
    return nd_figure_qs | stock_figure_qs


def update_public_figure_analysis():
    # NOTE:- Exactly one aggregation should obtained for PFA
    # NOTE:- There must be exaclty one country
    data = []

    # A PFA total is one of GiddDisplacement's two figure sums. Cause selects the rows, category
    # selects the column, so the four PFA aggregates are the 2x2 and no conditional sum is needed.
    sum_column_by_category = {
        Figure.FIGURE_CATEGORY_TYPES.IDPS: "total_displacement",
        Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT: "new_displacement",
    }

    # FIXME: only update the gidd_published_date when the report is stale
    # FIXME: gidd_published_date update looks redundant
    Report.objects.filter(
        is_gidd_report=True,
    ).update(gidd_published_date=timezone.now())

    visible_pfa_reports_qs = Report.objects.filter(
        is_pfa_visible_in_gidd=True,
        filter_figure_start_after__year__in=get_gidd_years(),
    )

    # FIXME: only update the gidd_published_date when the report is stale
    visible_pfa_reports_qs.update(
        gidd_published_date=timezone.now(),
        is_pfa_published_in_gidd=True,
    )

    # FIXME: add a cleanup function

    # PFA reads the GIDD displacement table rather than re-aggregating entry_figure per report.
    # The values are the same by construction: GiddDisplacement is grouped by country, year and
    # cause over `figures_in_year_window`, restricted to RECOMMENDED figures and to conflict and
    # disaster event types, which is what each PFA conditional sum selected. Its `year` values are
    # `get_gidd_years()` -- the same distinct `gidd_report_year` set the per-report loop keyed on.
    #
    # Summing the unrounded columns and rounding the total once is required: the table stores a
    # rounded value per typology row, and summing those rounds many times over and diverges.
    #
    # A country-year-cause with no figures in a category sums to NULL, not 0, and a missing group
    # is absent from the map -- PFA publishes `figures = None` for both, which callers rely on.
    #
    # Depends on `update_new_gidd_tables` having run: the table is populated in the same
    # transaction, earlier.
    #
    # The cause is the event's type, as it was before: a figure whose own `figure_cause` disagrees
    # with its event's type is counted under the event's.
    # TODO: nothing validates `figure_cause` against `event.event_type` on write.
    totals_by_year_country_cause = {
        (row["year"], row["country_id"], row["cause"]): row
        for row in GiddDisplacement.objects.values("year", "country_id", "cause")
        .order_by()
        .annotate(
            new_displacement=Sum("new_displacement"),
            total_displacement=Sum("total_displacement"),
        )
    }

    # `prefetch_related` batches the one-country-per-report reads that were an
    # extra query per report.
    for report in visible_pfa_reports_qs.prefetch_related("filter_figure_countries"):
        # PFA always have either IDPS or ND categories
        figure_category = report.filter_figure_categories[0]

        # PFA always have either conflict or disaster cause
        figure_cause = report.filter_figure_crisis_types[0]

        # Each PFA report needs exactly ONE of the two sums, on the rows for its own cause
        sum_column = sum_column_by_category.get(figure_category)

        # There must be exactly one country if is_pfa_visible_in_gidd is enabled.
        # This is validated in serializer
        country = report.filter_figure_countries.all()[0]
        iso3 = country.iso3

        figures_total = None
        if sum_column is not None:
            totals = totals_by_year_country_cause.get((report.filter_figure_end_before.year, country.id, figure_cause))
            if totals is not None:
                figures_total = totals[sum_column]

        data.append(
            PublicFigureAnalysis(
                # The report's id IS this row's key. There is exactly one analysis per
                # PFA-visible report, so the key is stable across releases even though the table
                # is emptied and rebuilt each time -- and a caller can reference a published
                # analysis without the number changing under it. This is the only path that
                # creates these rows, so every key is assigned here rather than by the sequence.
                id=report.id,
                iso3=iso3,
                figure_cause=figure_cause,
                figure_category=figure_category,
                year=report.filter_figure_end_before.year,
                figures=figures_total,
                figures_rounded=round_and_remove_zero(figures_total),
                description=report.public_figure_analysis,
                report=report,
                report_raw_id=report.id,
            ),
        )

    # Bulk create public analysis
    PublicFigureAnalysis.objects.bulk_create(data)


def update_idps_sadd_estimates_country_names():
    country_name_map = {
        country["id"]: country["idmc_short_name"] for country in Country.objects.values("id", "idmc_short_name")
    }
    estimates = list(IdpsSaddEstimate.objects.all())
    for obj in estimates:
        obj.country_name = country_name_map.get(obj.country_id)
    IdpsSaddEstimate.objects.bulk_update(estimates, ["country_name"], batch_size=2000)


def enum_label_text(value):
    """Text columns that store an enum's label got it implicitly: values()
    returns the enum member (django_enumfield converter) and TextField's
    str() coercion rendered the label on save. The raw-insert path must do
    the same explicitly — psycopg2 adapts int-like members as ints."""
    return None if value is None else str(value)


def bulk_insert_from_queryset(model, base_queryset, expressions, include_pk=False):
    """DB-side copy: everything stays in the ORM except the INSERT wrapper —
    Django has no INSERT ... SELECT-from-queryset. `expressions` maps
    attnames to ORM expressions; omitted columns get the model default
    (now() for auto_now*), matching `bulk_create`. Positional mapping:
    the INSERT column list follows `concrete_fields` order and the SELECT
    output follows the same-order annotation aliases."""
    now = timezone.now()
    fields = [field for field in model._meta.concrete_fields if include_pk or not field.primary_key]
    # An unrecognised key would otherwise be dropped and the column silently take its default:
    # an IntegrityError where the column is NOT NULL, a published table of NULLs where it is not.
    unknown = set(expressions) - {field.attname for field in fields}
    if unknown:
        raise ValueError("{} has no column(s) {}".format(model.__name__, ", ".join(sorted(unknown))))
    aliases = {}
    for field in fields:
        expression = expressions.get(field.attname)
        if expression is None:
            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                expression = Value(now, output_field=field)
            elif field.has_default():
                expression = Value(field.get_default(), output_field=field)
            else:
                expression = Value(None, output_field=field)
        # Prefixed aliases: annotate() rejects names that collide with the
        # source model's fields.
        aliases["gidd_{}".format(field.attname)] = expression
    queryset = base_queryset.annotate(**aliases).values(*aliases.keys())
    sql, params = queryset.query.sql_with_params()
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO {} ({}) {}".format(
                model._meta.db_table,
                ", ".join('"{}"'.format(field.column) for field in fields),
                sql,
            ),
            params,
        )


def update_gidd_event_and_gidd_figure_data():
    """
    Updates GiddEvent and GiddFigure data
    """

    # Grouping EventCode directly (instead of ArrayAgg over the LOUTER join)
    # sidesteps the all-NULL tuple that the python extractor used to skip;
    # the shared `ordering` keeps the per-column arrays aligned and matches
    # the old distinct-tuple sort (ids are compared as TEXT there).
    event_code_tuple = Array(
        Cast(models.F("id"), models.CharField()),
        models.F("event_code"),
        Cast(models.F("event_code_type"), models.CharField()),
        models.F("country__iso3"),
        output_field=ArrayField(models.CharField()),
    )
    event_code_cte = With(
        EventCode.objects.annotate(code_tuple=event_code_tuple)
        .order_by()
        .values("event")
        .annotate(
            ids=ArrayAgg("id", ordering="code_tuple"),
            codes=ArrayAgg("event_code", ordering="code_tuple"),
            types=ArrayAgg("event_code_type", ordering="code_tuple"),
            iso3s=ArrayAgg("country__iso3", ordering="code_tuple"),
        )
        .values("event", "ids", "codes", "types", "iso3s"),
        name="gidd_event_code_agg",
    )

    # NOTE: We are copying all the events; GiddEvent ID is same as Event ID
    bulk_insert_from_queryset(
        GiddEvent,
        event_code_cte.join(Event.objects.all(), id=event_code_cte.col.event_id, _join_type=LOUTER).with_cte(event_code_cte),
        dict(
            id=F("id"),
            event_id=F("id"),
            event_raw_id=F("id"),
            name=F("name"),
            cause=F("event_type"),
            start_date=F("start_date"),
            start_date_accuracy=F("start_date_accuracy"),
            end_date=F("end_date"),
            end_date_accuracy=F("end_date_accuracy"),
            violence_id=F("violence_id"),
            violence_sub_type_id=F("violence_sub_type_id"),
            disaster_category_id=F("disaster_category_id"),
            disaster_sub_category_id=F("disaster_sub_category_id"),
            disaster_type_id=F("disaster_type_id"),
            disaster_sub_type_id=F("disaster_sub_type_id"),
            other_sub_type_id=F("other_sub_type_id"),
            osv_sub_type_id=F("osv_sub_type_id"),
            violence_name=F("violence__name"),
            violence_sub_type_name=F("violence_sub_type__name"),
            disaster_category_name=F("disaster_category__name"),
            disaster_sub_category_name=F("disaster_sub_category__name"),
            disaster_type_name=F("disaster_type__name"),
            disaster_sub_type_name=F("disaster_sub_type__name"),
            other_sub_type_name=F("other_sub_type__name"),
            osv_sub_type_name=F("osv_sub_type__name"),
            event_codes_ids=Coalesce(event_code_cte.col.ids, empty_int_array()),
            event_codes=Coalesce(event_code_cte.col.codes, empty_char_array()),
            event_codes_type=Coalesce(event_code_cte.col.types, empty_int_array()),
            event_codes_iso3=Coalesce(event_code_cte.col.iso3s, empty_char_array()),
        ),
        include_pk=True,
    )

    # DB-side copy for GiddFigure, one INSERT..SELECT per GIDD year: each
    # to-many relation aggregates in its own figure-grouped CTE (no cartesian
    # fan-out) with per-column ArrayAggs sharing one tuple `ordering` —
    # aligned arrays in the old distinct-tuple sort order (elements compared
    # as TEXT there).
    for year in get_gidd_years():
        figure_base = figures_in_year_window(year)

        sources_order = Array(
            Cast("sources__id", models.CharField()),
            F("sources__name"),
            F("sources__organization_kind__name"),
            output_field=ArrayField(models.CharField()),
        )
        sources_filter = Q(entry__is_confidential=False, sources__isnull=False)
        sources_cte = With(
            figure_base.order_by()
            .values("id")
            .annotate(
                ids=ArrayAgg("sources__id", ordering=sources_order, filter=sources_filter),
                names=ArrayAgg("sources__name", ordering=sources_order, filter=sources_filter),
                types=ArrayAgg("sources__organization_kind__name", ordering=sources_order, filter=sources_filter),
            )
            .values("id", "ids", "names", "types"),
            name="gidd_figure_sources_agg",
        )

        locations_coordinates = Concat(
            F("geo_locations__lat"),
            Value(EXTERNAL_TUPLE_SEPARATOR),
            F("geo_locations__lon"),
            output_field=models.CharField(),
        )
        locations_order = Array(
            Cast("geo_locations__id", models.CharField()),
            F("geo_locations__display_name"),
            locations_coordinates,
            Cast("geo_locations__accuracy", models.CharField()),
            Cast("geo_locations__identifier", models.CharField()),
            output_field=ArrayField(models.CharField()),
        )
        locations_filter = Q(geo_locations__display_name__isnull=False) & ~Q(geo_locations__display_name="")
        locations_cte = With(
            figure_base.order_by()
            .values("id")
            .annotate(
                ids=ArrayAgg("geo_locations__id", ordering=locations_order, filter=locations_filter),
                # The old extractor `.strip()`ed the name AFTER the sort — the
                # ordering above uses the raw name.
                names=ArrayAgg(
                    Func(F("geo_locations__display_name"), Value(" \t\n\r\x0b\x0c"), function="BTRIM"),
                    ordering=locations_order,
                    filter=locations_filter,
                ),
                coordinates=ArrayAgg(locations_coordinates, ordering=locations_order, filter=locations_filter),
                accuracies=ArrayAgg("geo_locations__accuracy", ordering=locations_order, filter=locations_filter),
                types=ArrayAgg("geo_locations__identifier", ordering=locations_order, filter=locations_filter),
            )
            .values("id", "ids", "names", "coordinates", "accuracies", "types"),
            name="gidd_figure_locations_agg",
        )

        publishers_order = Array(
            Cast("entry__publishers__id", models.CharField()),
            F("entry__publishers__name"),
            F("entry__publishers__organization_kind__name"),
            output_field=ArrayField(models.CharField()),
        )
        publishers_filter = Q(entry__is_confidential=False, entry__publishers__name__isnull=False)
        publishers_cte = With(
            figure_base.order_by()
            .values("id")
            .annotate(
                ids=ArrayAgg("entry__publishers__id", ordering=publishers_order, filter=publishers_filter),
                names=ArrayAgg("entry__publishers__name", ordering=publishers_order, filter=publishers_filter),
                types=ArrayAgg(
                    "entry__publishers__organization_kind__name", ordering=publishers_order, filter=publishers_filter
                ),
            )
            .values("id", "ids", "names", "types"),
            name="gidd_figure_publishers_agg",
        )

        context_of_violence_order = Array(
            Cast("context_of_violence__id", models.CharField()),
            F("context_of_violence__name"),
            output_field=ArrayField(models.CharField()),
        )
        context_of_violence_filter = Q(context_of_violence__name__isnull=False)
        context_of_violence_cte = With(
            figure_base.order_by()
            .values("id")
            .annotate(
                ids=ArrayAgg(
                    "context_of_violence__id", ordering=context_of_violence_order, filter=context_of_violence_filter
                ),
                names=ArrayAgg(
                    "context_of_violence__name", ordering=context_of_violence_order, filter=context_of_violence_filter
                ),
            )
            .values("id", "ids", "names"),
            name="gidd_figure_context_of_violence_agg",
        )

        tags_order = Array(
            Cast("tags__id", models.CharField()),
            F("tags__name"),
            output_field=ArrayField(models.CharField()),
        )
        tags_filter = Q(tags__name__isnull=False)
        tags_cte = With(
            figure_base.order_by()
            .values("id")
            .annotate(
                ids=ArrayAgg("tags__id", ordering=tags_order, filter=tags_filter),
                names=ArrayAgg("tags__name", ordering=tags_order, filter=tags_filter),
            )
            .values("id", "ids", "names"),
            name="gidd_figure_tags_agg",
        )

        figure_query = figure_base.annotate(**Figure.annotate_stock_and_flow_dates())
        for cte in (sources_cte, locations_cte, publishers_cte, context_of_violence_cte, tags_cte):
            figure_query = cte.join(figure_query, id=cte.col.id, _join_type=LOUTER).with_cte(cte)

        bulk_insert_from_queryset(
            GiddFigure,
            figure_query,
            dict(
                # FIXME: Use figure id as pk on next release
                iso3=F("country__iso3"),
                figure_id=F("id"),
                figure_raw_id=F("id"),
                country_name=F("country__idmc_short_name"),
                country_id=F("country_id"),
                # NOTE: GiddEvent ID is same as Event ID
                gidd_event_id=F("event_id"),
                geographical_region_name=F("country__geographical_group__name"),
                year=Value(year, output_field=IntegerField()),
                unit=F("unit"),
                category=F("category"),
                cause=F("figure_cause"),
                term=F("term"),
                role=F("role"),
                quantifier=F("quantifier"),
                source_excerpt=F("source_excerpt"),
                calculation_logic=F("calculation_logic"),
                is_disaggregated=F("is_disaggregated"),
                entry_id=F("entry_id"),
                entry_raw_id=F("entry_id"),
                entry_name=F("entry__article_title"),
                publishers=Coalesce(publishers_cte.col.names, empty_char_array()),
                publishers_ids=Coalesce(publishers_cte.col.ids, empty_int_array()),
                publishers_type=Coalesce(publishers_cte.col.types, empty_char_array()),
                context_of_violence=Coalesce(context_of_violence_cte.col.names, empty_char_array()),
                context_of_violence_ids=Coalesce(context_of_violence_cte.col.ids, empty_int_array()),
                tags=Coalesce(tags_cte.col.names, empty_char_array()),
                tags_ids=Coalesce(tags_cte.col.ids, empty_int_array()),
                sources=Coalesce(sources_cte.col.names, empty_char_array()),
                sources_ids=Coalesce(sources_cte.col.ids, empty_int_array()),
                sources_type=Coalesce(sources_cte.col.types, empty_char_array()),
                total_figures=F("total_figures"),
                household_size=F("household_size"),
                reported=F("reported"),
                start_date=F("flow_start_date"),
                start_date_accuracy=F("flow_start_date_accuracy"),
                end_date=F("flow_end_date"),
                end_date_accuracy=F("flow_end_date_accuracy"),
                stock_date=F("stock_date"),
                stock_date_accuracy=F("stock_date_accuracy"),
                stock_reporting_date=F("stock_reporting_date"),
                is_housing_destruction=F("is_housing_destruction"),
                displacement_occurred=F("displacement_occurred"),
                include_idu=F("include_idu"),
                excerpt_idu=F("excerpt_idu"),
                is_confidential=F("entry__is_confidential"),
                locations_ids=Coalesce(locations_cte.col.ids, empty_int_array()),
                locations_names=Coalesce(locations_cte.col.names, empty_char_array()),
                locations_coordinates=Coalesce(locations_cte.col.coordinates, empty_char_array()),
                locations_accuracy=Coalesce(locations_cte.col.accuracies, empty_int_array()),
                locations_type=Coalesce(locations_cte.col.types, empty_int_array()),
                # violence_id / violence_sub_type_id stay NULL: the previous
                # pipeline fetched them but never wrote them (only the *_name
                # copies below).
                disaster_category_id=F("disaster_category_id"),
                disaster_sub_category_id=F("disaster_sub_category_id"),
                disaster_type_id=F("disaster_type_id"),
                disaster_sub_type_id=F("disaster_sub_type_id"),
                other_sub_type_id=F("other_sub_type_id"),
                osv_sub_type_id=F("osv_sub_type_id"),
                violence_name=F("violence__name"),
                violence_sub_type_name=F("violence_sub_type__name"),
                disaster_category_name=F("disaster_category__name"),
                disaster_sub_category_name=F("disaster_sub_category__name"),
                disaster_type_name=F("disaster_type__name"),
                disaster_sub_type_name=F("disaster_sub_type__name"),
                other_sub_type_name=F("other_sub_type__name"),
                osv_sub_type_name=F("osv_sub_type__name"),
            ),
        )


def _event_code_sort_tuple():
    """The tuple the old `ArrayAgg(Array(...), distinct=True)` sorted on.

    Per-column ArrayAggs share this `ordering` so the code and type-label arrays stay aligned in
    that order. The dedupe is dropped because PG rejects `array_agg(DISTINCT x ORDER BY y)`; no
    duplicate (event, code, type, country) tuple exists in the data, though EventCode carries no
    unique constraint to guarantee it.
    """
    return Array(
        F("event_code"),
        Cast(models.F("event_code_type"), models.CharField()),
        F("country__iso3"),
        output_field=ArrayField(models.CharField()),
    )


def _country_event_code_cte():
    """Codes for one (event, country) -- what GiddEventDisplacement.event_codes carries.

    Scoped to the row's own country, unlike `_all_country_event_code_cte`, which spans every
    country of the event.
    """
    return With(
        EventCode.objects.annotate(code_tuple=_event_code_sort_tuple())
        .order_by()
        .values("event", "country")
        .annotate(
            codes=ArrayAgg("event_code", ordering="code_tuple"),
            type_labels=ArrayAgg(enum_label_case("event_code_type", EventCode.EVENT_CODE_TYPE), ordering="code_tuple"),
        )
        .values("event", "country", "codes", "type_labels"),
        name="gidd_event_code_by_country",
    )


def _displacement_sums():
    """The two figure sums every GIDD displacement row carries.

    Left NULL when a category is absent -- a country-year with no conflict publishes NULL, not 0,
    and the REST layer's conditional sums depend on that.
    """
    return dict(
        new_displacement=Sum(
            Case(
                When(category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT, then=F("total_figures")),
                output_field=IntegerField(),
            )
        ),
        total_displacement=Sum(
            Case(
                When(category=Figure.FIGURE_CATEGORY_TYPES.IDPS, then=F("total_figures")),
                output_field=IntegerField(),
            )
        ),
    )


def update_new_gidd_tables():
    """Populate GiddEventDisplacement, then derive GiddDisplacement from it.

    Two INSERT..SELECTs per GIDD year plus one rollup: no row round-trips through the worker, and
    the rollup is a plain GROUP BY over rows written earlier in the same transaction -- which is
    why the two must not be split across transactions.
    """
    country_codes = _country_event_code_cte()
    all_codes = _all_country_event_code_cte()

    def _with_country_codes(base):
        base = country_codes.join(
            base,
            event_id=country_codes.col.event_id,
            country_id=country_codes.col.country_id,
            _join_type=LOUTER,
        ).with_cte(country_codes)
        return all_codes.join(base, event_id=all_codes.col.event_id, _join_type=LOUTER).with_cte(all_codes)

    def _shared_columns(year):
        return dict(
            event_id=F("event__id"),
            event_raw_id=F("event__id"),
            event_name=F("event__name"),
            # A column, not an enum literal: the queryset is filtered on it, so it is provably
            # this year's cause without relying on psycopg2 adapting an IntEnum member.
            cause=F("event__event_type"),
            year=Value(year, output_field=IntegerField()),
            country_id=F("country"),
            iso3=F("country__iso3"),
            country_name=F("country__idmc_short_name"),
            start_date=F("event__start_date"),
            end_date=F("event__end_date"),
            # The column is NOT NULL and a LEFT JOIN onto an event with no codes yields NULL; the
            # raw-insert path never runs the aggregate's convert_value, so nothing else fills it.
            event_codes=Coalesce(country_codes.col.codes, empty_char_array()),
            event_codes_type=Coalesce(country_codes.col.type_labels, empty_char_array()),
            all_country_event_codes=Coalesce(all_codes.col.codes, empty_char_array()),
            all_country_event_codes_type=Coalesce(all_codes.col.type_labels, empty_char_array()),
            new_displacement=F("new_displacement"),
            total_displacement=F("total_displacement"),
            new_displacement_rounded=rounded_figure_expr("new_displacement"),
            total_displacement_rounded=rounded_figure_expr("total_displacement"),
        )

    for year in get_gidd_years():
        conflict_figure_qs = figures_in_year_window(year, Crisis.CRISIS_TYPE.CONFLICT)
        conflict_base = (
            Figure.objects.filter(id__in=conflict_figure_qs.values("id"))
            .order_by()
            .values(
                "event__id",
                "event__event_type",
                "event__name",
                "event__start_date",
                "event__end_date",
                "event__violence",
                "event__violence__name",
                "event__violence_sub_type",
                "event__violence_sub_type__name",
                "country",
                "country__iso3",
                "country__idmc_short_name",
            )
            .annotate(**_displacement_sums())
        )
        bulk_insert_from_queryset(
            GiddEventDisplacement,
            _with_country_codes(conflict_base),
            dict(
                _shared_columns(year),
                violence_id=F("event__violence"),
                violence_name=F("event__violence__name"),
                violence_sub_type_id=F("event__violence_sub_type"),
                violence_sub_type_name=F("event__violence_sub_type__name"),
                displacement_occurred=empty_int_array(),
            ),
        )

        disaster_figure_qs = figures_in_year_window(year, Crisis.CRISIS_TYPE.DISASTER)
        disaster_base = (
            Figure.objects.filter(id__in=disaster_figure_qs.values("id"))
            .order_by()
            .values(
                "event__id",
                "event__event_type",
                "event__name",
                "event__start_date",
                "event__end_date",
                "event__start_date_accuracy",
                "event__end_date_accuracy",
                "event__disaster_category",
                "event__disaster_category__name",
                "event__disaster_sub_category",
                "event__disaster_sub_category__name",
                "event__disaster_type",
                "event__disaster_type__name",
                "event__disaster_sub_type",
                "event__disaster_sub_type__name",
                "country",
                "country__iso3",
                "country__idmc_short_name",
            )
            .annotate(**_displacement_sums())
        )
        bulk_insert_from_queryset(
            GiddEventDisplacement,
            _with_country_codes(disaster_base),
            dict(
                _shared_columns(year),
                # CASE-mapped, not F(): the raw-insert path bypasses the TextField str()
                # coercion that rendered these labels, so a bare F() publishes the digits.
                start_date_accuracy=enum_label_case(
                    "event__start_date_accuracy", Event._meta.get_field("start_date_accuracy").enum
                ),
                end_date_accuracy=enum_label_case(
                    "event__end_date_accuracy", Event._meta.get_field("end_date_accuracy").enum
                ),
                displacement_occurred=Coalesce(
                    ArrayAgg(
                        F("displacement_occurred"),
                        distinct=True,
                        filter=Q(displacement_occurred__isnull=False),
                    ),
                    empty_int_array(),
                ),
                hazard_category_id=F("event__disaster_category"),
                hazard_category_name=F("event__disaster_category__name"),
                hazard_sub_category_id=F("event__disaster_sub_category"),
                hazard_sub_category_name=F("event__disaster_sub_category__name"),
                hazard_type_id=F("event__disaster_type"),
                hazard_type_name=F("event__disaster_type__name"),
                hazard_sub_type_id=F("event__disaster_sub_type"),
                hazard_sub_type_name=F("event__disaster_sub_type__name"),
            ),
        )

    # One pass covers both causes: `cause` is a group key, conflict rows carry NULL in every hazard
    # column and disaster rows NULL in both violence columns, and PG groups NULLs as equal.
    # `nd`/`td`, not the field names -- annotate() refuses a name that collides with a model field.
    rollup = (
        GiddEventDisplacement.objects.order_by()
        .values(
            "year",
            "cause",
            "country_id",
            "iso3",
            "country_name",
            "violence_id",
            "violence_name",
            "violence_sub_type_id",
            "violence_sub_type_name",
            "hazard_category_id",
            "hazard_category_name",
            "hazard_sub_category_id",
            "hazard_sub_category_name",
            "hazard_type_id",
            "hazard_type_name",
            "hazard_sub_type_id",
            "hazard_sub_type_name",
        )
        .annotate(nd=Sum("new_displacement"), td=Sum("total_displacement"))
    )
    bulk_insert_from_queryset(
        GiddDisplacement,
        rollup,
        dict(
            year=F("year"),
            cause=F("cause"),
            country_id=F("country_id"),
            iso3=F("iso3"),
            country_name=F("country_name"),
            violence_id=F("violence_id"),
            violence_name=F("violence_name"),
            violence_sub_type_id=F("violence_sub_type_id"),
            violence_sub_type_name=F("violence_sub_type_name"),
            hazard_category_id=F("hazard_category_id"),
            hazard_category_name=F("hazard_category_name"),
            hazard_sub_category_id=F("hazard_sub_category_id"),
            hazard_sub_category_name=F("hazard_sub_category_name"),
            hazard_type_id=F("hazard_type_id"),
            hazard_type_name=F("hazard_type_name"),
            hazard_sub_type_id=F("hazard_sub_type_id"),
            hazard_sub_type_name=F("hazard_sub_type_name"),
            new_displacement=F("nd"),
            total_displacement=F("td"),
            new_displacement_rounded=rounded_figure_expr("nd"),
            total_displacement_rounded=rounded_figure_expr("td"),
        ),
    )


# Hard ceiling for one generation run (currently ~12 min in production). The soft
# limit raises inside the task so the run rolls back and marks itself FAILED; the
# hard limit is the kill-switch backstop. The lock TTL must stay ABOVE the hard
# limit: if the lock expired mid-run, a second generation could start — and under
# READ COMMITTED its DELETE cannot see the first run's uncommitted inserts, so
# both row sets would COMMIT.
GIDD_GENERATION_TIMEOUT = 60 * 30
GIDD_GENERATION_LOCK_KEY = "update_gidd_data"
GIDD_GENERATION_LOCK_TTL = GIDD_GENERATION_TIMEOUT + 60 * 5


def _all_country_event_code_cte():
    """An event's codes across ALL its countries.

    The shape the REST disaster payload publishes: a country that registered a code but produced
    no figures has no row of its own, so aggregating over rows would drop its code.
    `GiddEventDisplacement.event_codes` stays country-correct.
    """
    return With(
        EventCode.objects.annotate(code_tuple=_event_code_sort_tuple())
        .order_by()
        .values("event")
        .annotate(
            codes=ArrayAgg("event_code", ordering="code_tuple"),
            type_labels=ArrayAgg(enum_label_case("event_code_type", EventCode.EVENT_CODE_TYPE), ordering="code_tuple"),
        )
        .values("event", "codes", "type_labels"),
        name="witness_event_code_all_countries",
    )


@redis_lock(GIDD_GENERATION_LOCK_KEY, GIDD_GENERATION_LOCK_TTL)
def _generate_gidd_data(log_id):
    try:
        with transaction.atomic():
            # DELETE
            # -- Delete all the public figure analysis objects
            PublicFigureAnalysis.objects.all().delete()
            # -- Delete all the GiddFigure objects
            GiddFigure.objects.all().delete()
            # -- Delete all the GiddEvent objects
            GiddEvent.objects.all().delete()
            GiddEventDisplacement.objects.all().delete()
            GiddDisplacement.objects.all().delete()

            # Create new data for GIDD
            update_idps_sadd_estimates_country_names()
            update_gidd_event_and_gidd_figure_data()
            update_new_gidd_tables()
            # After update_new_gidd_tables: reads the GiddDisplacement rows it writes.
            update_public_figure_analysis()
            StatusLog.objects.filter(id=log_id).update(status=StatusLog.Status.SUCCESS, completed_at=timezone.now())
        logger.info("GIDD data updated.")
    except Exception as e:
        StatusLog.objects.filter(id=log_id).update(status=StatusLog.Status.FAILED, completed_at=timezone.now())
        logger.error("Failed update data: " + str(e), exc_info=True)


@celery_app.task(soft_time_limit=GIDD_GENERATION_TIMEOUT, time_limit=GIDD_GENERATION_TIMEOUT + 120)
def update_gidd_data(log_id):
    # redis_lock is non-blocking and returns False when another generation holds
    # the lock: the losing run must never reach the delete+rebuild (the mutations'
    # pending-run guard is only advisory — mutation races and celery redelivery
    # bypass it).
    if _generate_gidd_data(log_id=log_id) is False:
        StatusLog.objects.filter(id=log_id).update(status=StatusLog.Status.FAILED, completed_at=timezone.now())
        logger.error("Another GIDD generation is already running; refused to run concurrently.")


@celery_app.task
def kill_all_stale_gidd_generations():
    """A worker killed hard (OOM, deploy, the time_limit backstop) rolls back its
    transaction but leaves its StatusLog PENDING forever — flip those to FAILED so
    the run's fate is visible and triggers are never blocked by a dead run."""
    updated = StatusLog.objects.filter(
        status=StatusLog.Status.PENDING,
        triggered_at__lt=timezone.now() - StatusLog.PENDING_STALE_AFTER,
    ).update(status=StatusLog.Status.FAILED, completed_at=timezone.now())
    if updated:
        logger.error(f"Marked {updated} stale GIDD generation(s) as failed.")
