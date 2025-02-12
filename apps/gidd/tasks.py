import datetime
import logging
from helix.celery import app as celery_app
from django.utils import timezone
from django.db import models, transaction
from django.db.models.functions import Cast, Concat, Coalesce
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db.models import (
    Sum, Case, When, IntegerField, Value, F, Subquery, OuterRef, Q
)
from django.contrib.postgres.fields import ArrayField

from utils.common import round_and_remove_zero
from apps.entry.models import Figure
from apps.event.models import Crisis, EventCode
from .models import (
    GiddEvent,
    GiddFigure,
    StatusLog,
    DisasterLegacy,
    ConflictLegacy,
    PublicFigureAnalysis,
    Conflict,
    Disaster,
    DisplacementData,
    IdpsSaddEstimate,
)
from apps.event.models import Event
from apps.country.models import Country
from apps.report.models import Report
from apps.common.utils import (
    EXTERNAL_TUPLE_SEPARATOR,
    extract_event_code_data_list,
    extract_event_code_data_raw_list,
    extract_location_raw_data_list,
    extract_source_data,
    extract_publisher_data,
    extract_context_of_voilence_raw_data_list,
    extract_tag_raw_data_list,
)
from utils.db import Array


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_gidd_years():
    return Report.objects.filter(is_gidd_report=True)\
        .order_by('gidd_report_year')\
        .distinct('gidd_report_year')\
        .values_list('gidd_report_year', flat=True)


def annotate_conflict(qs, year):
    return qs.annotate(
        year=Value(year, output_field=IntegerField()),
    ).values('year', 'country__idmc_short_name', 'country__iso3').annotate(
        total_displacement=Sum(
            Case(
                When(
                    category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                    then=F('total_figures')
                ),
                output_field=IntegerField(),
            )
        ),
        new_displacement=Sum(
            Case(
                When(
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    then=F('total_figures')
                ),
                output_field=IntegerField(),
            )
        ),
        country=F('country'),
    ).order_by('year')


def update_gidd_legacy_data():
    iso3_to_country_id_map = {
        country['iso3']: country['id'] for country in Country.objects.values('iso3', 'id')
    }
    iso3_to_country_name_map = {
        country['iso3']: country['idmc_short_name'] for country in Country.objects.values('iso3', 'idmc_short_name')
    }

    # Bulk create conflict legacy data
    Conflict.objects.bulk_create(
        [
            Conflict(
                total_displacement=item['total_displacement'],
                new_displacement=item['new_displacement'],
                total_displacement_rounded=round_and_remove_zero(
                    item['total_displacement']
                ),
                new_displacement_rounded=round_and_remove_zero(
                    item['new_displacement']
                ),
                year=item['year'],
                iso3=item['iso3'],
                country_id=iso3_to_country_id_map[item['iso3']],
                country_name=iso3_to_country_name_map[item['iso3']],
            ) for item in ConflictLegacy.objects.values(
                'total_displacement',
                'new_displacement',
                'year',
                'iso3',
            )
        ]
    )

    # Bulk create legacy disaster data
    Disaster.objects.bulk_create(
        [
            Disaster(
                event_name=item['event_name'],
                year=item['year'],
                start_date=item['start_date'],
                start_date_accuracy=item['start_date_accuracy'],
                end_date=item['end_date'],
                end_date_accuracy=item['end_date_accuracy'],

                hazard_category_id=item['hazard_category'],
                hazard_sub_category_id=item['hazard_sub_category'],
                hazard_type_id=item['hazard_type'],
                hazard_sub_type_id=item['hazard_sub_type'],

                # FIXME: we should get this from database
                hazard_category_name=item['hazard_category__name'],
                hazard_sub_category_name=item['hazard_sub_category__name'],
                hazard_type_name=item['hazard_type__name'],
                hazard_sub_type_name=item['hazard_sub_type__name'],

                new_displacement=item['new_displacement'],

                new_displacement_rounded=round_and_remove_zero(
                    item['new_displacement']
                ),
                iso3=item['iso3'],
                country_id=iso3_to_country_id_map[item['iso3']],
                country_name=iso3_to_country_name_map[item['iso3']],
            ) for item in DisasterLegacy.objects.values(
                'event_name',
                'year',
                'start_date',
                'start_date_accuracy',
                'end_date',
                'end_date_accuracy',
                'hazard_category',
                'hazard_sub_category',
                'hazard_type',
                'hazard_sub_type',
                'hazard_category__name',
                'hazard_sub_category__name',
                'hazard_type__name',
                'hazard_sub_type__name',
                'new_displacement',
                'iso3',
            )
        ]
    )


def update_conflict_and_disaster_data():
    figure_queryset = Figure.objects.filter(
        role=Figure.ROLE.RECOMMENDED
    )
    for year in get_gidd_years():
        # FIXME: Check if this should be
        # - Figure.filtered_nd_figures_for_listing
        # - Figure.filtered_idp_figures_for_listing
        # NOTE: No we do not need to use the listing method as we are aggregating
        nd_figure_qs = Figure.filtered_nd_figures(
            qs=figure_queryset,
            start_date=datetime.datetime(year=year, month=1, day=1),
            end_date=datetime.datetime(year=year, month=12, day=31),
        )
        stock_figure_qs = Figure.filtered_idp_figures(
            qs=figure_queryset,
            start_date=datetime.datetime(year=year, month=1, day=1),
            end_date=datetime.datetime(year=year, month=12, day=31),
        )
        conflict_nd_figure_qs = nd_figure_qs.filter(event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
        conflict_stock_figure_qs = stock_figure_qs.filter(event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
        conflict_figure_qs = conflict_nd_figure_qs | conflict_stock_figure_qs
        qs = annotate_conflict(Figure.objects.filter(id__in=conflict_figure_qs.values('id')), year)

        # Create new conflict figures
        Conflict.objects.bulk_create(
            [
                Conflict(
                    country_id=figure['country'],
                    total_displacement=figure['total_displacement'],
                    new_displacement=figure['new_displacement'],
                    total_displacement_rounded=round_and_remove_zero(
                        figure['total_displacement']
                    ),
                    new_displacement_rounded=round_and_remove_zero(
                        figure['new_displacement']
                    ),
                    year=figure['year'],
                    iso3=figure['country__iso3'],
                    country_name=figure['country__idmc_short_name'],
                ) for figure in qs
            ]
        )

        disaster_nd_figure_qs = nd_figure_qs.filter(event__event_type=Crisis.CRISIS_TYPE.DISASTER)
        disaster_stock_figure_qs = stock_figure_qs.filter(event__event_type=Crisis.CRISIS_TYPE.DISASTER)
        disaster_figures = disaster_nd_figure_qs | disaster_stock_figure_qs
        disaster_qs = Figure.objects.filter(id__in=disaster_figures.values('id'))

        # Sync disaster data
        disasters = disaster_qs.values(
            'event__id',
            'event__name',
            'event__disaster_category',
            'event__disaster_sub_category',
            'event__disaster_type',
            'event__disaster_sub_type',
            'event__disaster_category__name',
            'event__disaster_sub_category__name',
            'event__disaster_type__name',
            'event__disaster_sub_type__name',
            'event__start_date',
            'event__end_date',
            'event__start_date_accuracy',
            'event__end_date_accuracy',
            'event__glide_numbers',
            'country',
            'country__iso3',
            'country__idmc_short_name',
        ).order_by().annotate(
            new_displacement=Sum(
                Case(
                    When(
                        category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                        then=F('total_figures')
                    ),
                    output_field=IntegerField(),
                )
            ),
            total_displacement=Sum(
                Case(
                    When(
                        category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                        then=F('total_figures')
                    ),
                    output_field=IntegerField(),
                )
            ),
            year=Value(year, output_field=IntegerField()),
            event_codes=Coalesce(
                Subquery(
                    EventCode.objects.filter(
                        event_id=OuterRef('event'),
                        country_id=F('country')
                    ).order_by().values('event')
                    .annotate(
                        code=ArrayAgg(
                            Array(
                                F('event_code'),
                                Cast(models.F('event_code_type'), models.CharField()),
                                F('country__iso3'),
                                output_field=ArrayField(models.CharField()),
                            ),
                            distinct=True,
                        ),
                    ).values('code')[:1],
                ),
                [],
            ),
            _displacement_occurred=ArrayAgg(
                F('displacement_occurred'),
                distinct=True,
                filter=Q(displacement_occurred__isnull=False),
            ),
        ).filter(
            year__gte=2016,
        )

        Disaster.objects.bulk_create(
            [
                Disaster(
                    event_id=item['event__id'],
                    event_raw_id=item['event__id'],
                    event_name=item['event__name'],
                    year=item['year'],
                    start_date=item['event__start_date'],
                    start_date_accuracy=item['event__start_date_accuracy'],
                    end_date=item['event__end_date'],
                    end_date_accuracy=item['event__end_date_accuracy'],

                    hazard_category_id=item['event__disaster_category'],
                    hazard_sub_category_id=item['event__disaster_sub_category'],
                    hazard_type_id=item['event__disaster_type'],
                    hazard_sub_type_id=item['event__disaster_sub_type'],

                    hazard_category_name=item['event__disaster_category__name'],
                    hazard_sub_category_name=item['event__disaster_sub_category__name'],
                    hazard_type_name=item['event__disaster_type__name'],
                    hazard_sub_type_name=item['event__disaster_sub_type__name'],
                    glide_numbers=item['event__glide_numbers'] or list(),

                    new_displacement=item['new_displacement'],
                    total_displacement=item['total_displacement'],
                    new_displacement_rounded=round_and_remove_zero(
                        item['new_displacement']
                    ),
                    total_displacement_rounded=round_and_remove_zero(
                        item['total_displacement']
                    ),
                    iso3=item['country__iso3'],
                    country_id=item['country'],
                    country_name=item['country__idmc_short_name'],
                    displacement_occurred=item['_displacement_occurred'] or [],
                    event_codes=event_code['code'],
                    event_codes_type=event_code['code_type']
                )
                for item in disasters
                for event_code in [extract_event_code_data_list(item['event_codes'])]
            ]
        )


def update_public_figure_analysis():
    # NOTE:- Exactly one aggregation should obtained for PFA
    # NOTE:- There must be exaclty one country
    data = []

    def _get_figures(figure_category, figure_cause, report_country_aggregation):
        if (
            figure_category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
            figure_cause == Crisis.CRISIS_TYPE.CONFLICT
        ):
            return report_country_aggregation['total_stock_conflict']
        elif (
            figure_category == Figure.FIGURE_CATEGORY_TYPES.IDPS and
            figure_cause == Crisis.CRISIS_TYPE.DISASTER
        ):
            return report_country_aggregation['total_stock_disaster']
        elif (
            figure_category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
            figure_cause == Crisis.CRISIS_TYPE.CONFLICT
        ):
            return report_country_aggregation['total_flow_conflict']
        elif (
            figure_category == Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT and
            figure_cause == Crisis.CRISIS_TYPE.DISASTER
        ):
            return report_country_aggregation['total_flow_disaster']

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

    for report in visible_pfa_reports_qs:
        report_country_aggregation = report.report_figures.aggregate(
            **report.TOTAL_FIGURE_DISAGGREGATIONS,
        )

        # There must be exactly one country if is_pfa_visible_in_gidd is enabled.
        # This is validated in serializer
        iso3 = report.filter_figure_countries.first().iso3

        # PFA always have either IDPS or ND categories
        figure_category = report.filter_figure_categories[0]

        # PFA always have either conflict or disaster cause
        figure_cause = report.filter_figure_crisis_types[0]

        data.append(
            PublicFigureAnalysis(
                iso3=iso3,
                figure_cause=figure_cause,
                figure_category=figure_category,
                year=report.filter_figure_end_before.year,
                figures=_get_figures(figure_category, figure_cause, report_country_aggregation),
                figures_rounded=round_and_remove_zero(
                    _get_figures(figure_category, figure_cause, report_country_aggregation)
                ),
                description=report.public_figure_analysis,
                report=report,
                report_raw_id=report.id,
            ),
        )

    # Bulk create public analysis
    PublicFigureAnalysis.objects.bulk_create(data)


def update_displacement_data():
    start_year = min(
        Disaster.objects.order_by('year').first().year,
        Conflict.objects.order_by('year').first().year
    )
    end_year = max(
        Disaster.objects.order_by('-year').first().year,
        Conflict.objects.order_by('-year').first().year
    )

    for year in range(start_year, end_year + 1):
        displacement_data = Country.objects.annotate(
            conflict_total_displacement=Subquery(
                Conflict.objects.filter(
                    year=year,
                    country_id=OuterRef('pk'),
                ).values('total_displacement')[:1]
            ),
            conflict_new_displacement=Subquery(
                Conflict.objects.filter(
                    year=year,
                    country_id=OuterRef('pk'),
                ).values('new_displacement')[:1]
            ),
            disaster_total_displacement=Subquery(
                Disaster.objects.filter(
                    year=year,
                    country_id=OuterRef('pk'),
                ).values('iso3').order_by().annotate(
                    disaster_total_displacement=Sum('total_displacement')
                ).values('disaster_total_displacement')[:1]
            ),
            disaster_new_displacement=Subquery(
                Disaster.objects.filter(
                    year=year,
                    country_id=OuterRef('pk'),
                ).values('iso3').order_by().annotate(
                    disaster_new_displacement=Sum('new_displacement')
                ).values('disaster_new_displacement')[:1]
            ),
            year=Value(year, output_field=IntegerField()),
        ).filter(
            Q(conflict_new_displacement__isnull=False) |
            Q(conflict_total_displacement__isnull=False) |
            Q(disaster_new_displacement__isnull=False) |
            Q(disaster_total_displacement__isnull=False)
        ).values(
            'iso3',
            'idmc_short_name',
            'id',
            'conflict_total_displacement',
            'conflict_new_displacement',
            'disaster_new_displacement',
            'disaster_total_displacement',
            'year',
        )

        DisplacementData.objects.bulk_create(
            [
                DisplacementData(
                    iso3=item['iso3'],
                    country_name=item['idmc_short_name'],
                    country_id=item['id'],

                    conflict_total_displacement=item['conflict_total_displacement'],
                    conflict_new_displacement=item['conflict_new_displacement'],
                    disaster_new_displacement=item['disaster_new_displacement'],
                    disaster_total_displacement=item['disaster_total_displacement'],
                    conflict_total_displacement_rounded=round_and_remove_zero(
                        item['conflict_total_displacement']
                    ),
                    conflict_new_displacement_rounded=round_and_remove_zero(
                        item['conflict_new_displacement']
                    ),
                    disaster_new_displacement_rounded=round_and_remove_zero(
                        item['disaster_new_displacement']
                    ),
                    disaster_total_displacement_rounded=round_and_remove_zero(
                        item['disaster_total_displacement']
                    ),
                    year=item['year'],
                ) for item in displacement_data
            ]
        )


def update_idps_sadd_estimates_country_names():
    country_name_map = {
        country['id']: country['idmc_short_name'] for country in Country.objects.values('id', 'idmc_short_name')
    }
    for obj in IdpsSaddEstimate.objects.all():
        obj.country_name = country_name_map.get(obj.country_id)
        obj.save()


def update_gidd_event_and_gidd_figure_data():
    '''
    Updates GiddEvent and GiddFigure data
    '''

    event_queryset = Event.objects.annotate(
        event_codes=ArrayAgg(
            Array(
                Cast(models.F('event_code__id'), models.CharField()),
                models.F('event_code__event_code'),
                Cast(models.F('event_code__event_code_type'), models.CharField()),  # NOTE: ENUM is used instead of string
                models.F('event_code__country__iso3'),
                output_field=ArrayField(models.CharField()),
            ),
            distinct=True,
        ),
    ).values(
        'id',
        'name',
        'event_type',
        'start_date',
        'start_date_accuracy',
        'end_date',
        'end_date_accuracy',
        'violence',
        'violence__name',
        'violence_sub_type',
        'violence_sub_type__name',
        'disaster_category',
        'disaster_category__name',
        'disaster_sub_category',
        'disaster_sub_category__name',
        'disaster_type',
        'disaster_type__name',
        'disaster_sub_type',
        'disaster_sub_type__name',
        'other_sub_type',
        'other_sub_type__name',
        'osv_sub_type',
        'osv_sub_type__name',
        'event_codes',
    )

    # Create new GiddEvent
    GiddEvent.objects.bulk_create(
        [
            # NOTE: We are copying all the events
            GiddEvent(
                id=item['id'],  # NOTE: GiddEvent ID is same as Event ID
                event_id=item['id'],
                event_raw_id=item['id'],
                name=item['name'],
                cause=item['event_type'],

                start_date=item['start_date'],
                start_date_accuracy=item['start_date_accuracy'],
                end_date=item['end_date'],
                end_date_accuracy=item['end_date_accuracy'],

                violence_id=item['violence'],
                violence_sub_type_id=item['violence_sub_type'],

                disaster_category_id=item['disaster_category'],
                disaster_sub_category_id=item['disaster_sub_category'],
                disaster_type_id=item['disaster_type'],
                disaster_sub_type_id=item['disaster_sub_type'],
                other_sub_type_id=item['other_sub_type'],
                osv_sub_type_id=item['osv_sub_type'],

                violence_name=item['violence__name'],
                violence_sub_type_name=item['violence_sub_type__name'],
                disaster_category_name=item['disaster_category__name'],
                disaster_sub_category_name=item['disaster_sub_category__name'],
                disaster_type_name=item['disaster_type__name'],
                disaster_sub_type_name=item['disaster_sub_type__name'],
                other_sub_type_name=item['other_sub_type__name'],
                osv_sub_type_name=item['osv_sub_type__name'],

                event_codes_ids=event_code['id'],
                event_codes=event_code['code'],
                event_codes_type=event_code['code_type'],
                event_codes_iso3=event_code['iso3']
            ) for item in event_queryset
            for event_code in [extract_event_code_data_raw_list(item['event_codes'])]
        ]
    )

    for year in get_gidd_years():
        figure_queryset = Figure.objects.filter(
            role=Figure.ROLE.RECOMMENDED
        )
        nd_figure_qs = Figure.filtered_nd_figures(
            qs=figure_queryset,
            start_date=datetime.datetime(year=year, month=1, day=1),
            end_date=datetime.datetime(year=year, month=12, day=31),
        )
        stock_figure_qs = Figure.filtered_idp_figures(
            qs=figure_queryset,
            start_date=datetime.datetime(year=year, month=1, day=1),
            end_date=datetime.datetime(year=year, month=12, day=31),
        )
        figure_qs = nd_figure_qs | stock_figure_qs

        qs = figure_qs.annotate(
            **Figure.annotate_stock_and_flow_dates(),
            sources_data=ArrayAgg(
                Array(
                    Cast('sources__id', models.CharField()),
                    F('sources__name'),
                    F('sources__organization_kind__name'),
                    output_field=ArrayField(models.CharField()),
                ),
                distinct=True,
                filter=Q(entry__is_confidential=False)
            ),
            locations=ArrayAgg(
                Array(
                    Cast('geo_locations__id', models.CharField()),
                    F('geo_locations__display_name'),
                    Concat(
                        F('geo_locations__lat'),
                        Value(EXTERNAL_TUPLE_SEPARATOR),
                        F('geo_locations__lon'),
                        output_field=models.CharField(),
                    ),
                    # TODO: Fetch enum values instead of labels
                    Cast('geo_locations__accuracy', models.CharField()),
                    Cast('geo_locations__identifier', models.CharField()),
                    output_field=ArrayField(models.CharField()),
                ),
                distinct=True,
                filter=Q(
                    Q(geo_locations__display_name__isnull=False),
                    ~Q(geo_locations__display_name='')
                ),
            ),
            publishers_data=ArrayAgg(
                Array(
                    Cast('entry__publishers__id', models.CharField()),
                    F('entry__publishers__name'),
                    F('entry__publishers__organization_kind__name'),
                    output_field=ArrayField(models.CharField()),
                ),
                distinct=True,
                filter=Q(
                    entry__is_confidential=False,
                    entry__publishers__name__isnull=False,
                )
            ),
            context_of_violence_data=ArrayAgg(
                Array(
                    Cast('context_of_violence__id', models.CharField()),
                    F('context_of_violence__name'),
                    output_field=ArrayField(models.CharField()),
                ),
                distinct=True,
                filter=Q(context_of_violence__name__isnull=False),
            ),
            tags_data=ArrayAgg(
                Array(
                    Cast('tags__id', models.CharField()),
                    F('tags__name'),
                    output_field=ArrayField(models.CharField()),
                ),
                distinct=True,
                filter=Q(tags__name__isnull=False),
            ),
        ).values(
            'id',
            'event__id',
            'country',
            'country__iso3',
            'country__idmc_short_name',
            'country__geographical_group__name',
            'sources_data',
            'publishers_data',
            'locations',
            'unit',
            'quantifier',
            'role',
            'term',
            'category',
            'figure_cause',
            'total_figures',
            'household_size',
            'reported',
            'flow_start_date',
            'flow_start_date_accuracy',
            'flow_end_date',
            'flow_end_date_accuracy',
            'stock_date',
            'stock_date_accuracy',
            'stock_reporting_date',
            'is_housing_destruction',
            'include_idu',
            'excerpt_idu',
            'displacement_occurred',
            'violence',
            'violence__name',
            'violence_sub_type',
            'violence_sub_type__name',
            'disaster_category',
            'disaster_category__name',
            'disaster_sub_category',
            'disaster_sub_category__name',
            'disaster_type',
            'disaster_type__name',
            'disaster_sub_type',
            'disaster_sub_type__name',
            'other_sub_type',
            'other_sub_type__name',
            'osv_sub_type',
            'osv_sub_type__name',
            'source_excerpt',
            'calculation_logic',
            'is_disaggregated',
            'entry',
            'entry__article_title',
            'entry__is_confidential',
            'tags_data',
            'context_of_violence_data',
        )

        GiddFigure.objects.bulk_create(
            [
                GiddFigure(
                    # FIXME: Use this on next release
                    # id=item['id'],
                    iso3=item['country__iso3'],
                    figure_id=item['id'],
                    figure_raw_id=item['id'],
                    country_name=item['country__idmc_short_name'],
                    country_id=item['country'],
                    gidd_event_id=item['event__id'],    # NOTE: GiddEvent ID is same as Event ID
                    geographical_region_name=item['country__geographical_group__name'],
                    year=year,
                    unit=item['unit'],
                    category=item['category'],
                    cause=item['figure_cause'],
                    term=item['term'],
                    role=item['role'],
                    quantifier=item['quantifier'],
                    source_excerpt=item['source_excerpt'],
                    calculation_logic=item['calculation_logic'],
                    is_disaggregated=item['is_disaggregated'],
                    entry_id=item['entry'],
                    entry_raw_id=item['entry'],
                    entry_name=item['entry__article_title'],
                    publishers=publisher_data['publishers'],
                    publishers_ids=publisher_data['ids'],
                    publishers_type=publisher_data['publishers_type'],
                    context_of_violence=context_of_violence_data['context_of_violence'],
                    context_of_violence_ids=context_of_violence_data['ids'],
                    tags=tag_data['tags'],
                    tags_ids=tag_data['ids'],
                    sources=source_data['sources'],
                    sources_ids=source_data['ids'],
                    sources_type=source_data['sources_type'],
                    total_figures=item['total_figures'],
                    household_size=item['household_size'],
                    reported=item['reported'],
                    start_date=item['flow_start_date'],
                    start_date_accuracy=item['flow_start_date_accuracy'],
                    end_date=item['flow_end_date'],
                    end_date_accuracy=item['flow_end_date_accuracy'],
                    stock_date=item['stock_date'],
                    stock_date_accuracy=item['stock_date_accuracy'],
                    stock_reporting_date=item['stock_reporting_date'],
                    is_housing_destruction=item['is_housing_destruction'],
                    displacement_occurred=item['displacement_occurred'],
                    include_idu=item['include_idu'],
                    excerpt_idu=item['excerpt_idu'],
                    is_confidential=item['entry__is_confidential'],

                    locations_ids=location_data['ids'],
                    locations_names=location_data['display_name'],
                    locations_coordinates=location_data['lat_lon'],
                    locations_accuracy=location_data['accuracy'],
                    locations_type=location_data['type_of_points'],

                    disaster_category_id=item['disaster_category'],
                    disaster_sub_category_id=item['disaster_sub_category'],
                    disaster_type_id=item['disaster_type'],
                    disaster_sub_type_id=item['disaster_sub_type'],
                    other_sub_type_id=item['other_sub_type'],
                    osv_sub_type_id=item['osv_sub_type'],

                    violence_name=item['violence__name'],
                    violence_sub_type_name=item['violence_sub_type__name'],
                    disaster_category_name=item['disaster_category__name'],
                    disaster_sub_category_name=item['disaster_sub_category__name'],
                    disaster_type_name=item['disaster_type__name'],
                    disaster_sub_type_name=item['disaster_sub_type__name'],
                    other_sub_type_name=item['other_sub_type__name'],
                    osv_sub_type_name=item['osv_sub_type__name'],
                ) for item in qs
                for location_data in [extract_location_raw_data_list(item['locations'])]
                for source_data in [extract_source_data(item['sources_data'])]
                for publisher_data in [extract_publisher_data(item['publishers_data'])]
                for context_of_violence_data in [extract_context_of_voilence_raw_data_list(item['context_of_violence_data'])]
                for tag_data in [extract_tag_raw_data_list(item['tags_data'])]
            ]
        )


@celery_app.task
def update_gidd_data(log_id):
    try:
        with transaction.atomic():
            # DELETE
            # -- Delete all the conflicts TODO: Find way to update records
            Conflict.objects.all().delete()
            # -- Delete disasters
            Disaster.objects.all().delete()
            # -- Delete all the public figure analysis objects
            PublicFigureAnalysis.objects.all().delete()
            DisplacementData.objects.all().delete()
            # -- Delete all the GiddFigure objects
            GiddFigure.objects.all().delete()
            # -- Delete all the GiddEvent objects
            GiddEvent.objects.all().delete()

            # Create new data for GIDD
            update_gidd_legacy_data()
            update_conflict_and_disaster_data()
            update_public_figure_analysis()
            update_displacement_data()
            update_idps_sadd_estimates_country_names()
            update_gidd_event_and_gidd_figure_data()
            StatusLog.objects.filter(id=log_id).update(
                status=StatusLog.Status.SUCCESS,
                completed_at=timezone.now()
            )
        logger.info('GIDD data updated.')
    except Exception as e:
        StatusLog.objects.filter(id=log_id).update(
            status=StatusLog.Status.FAILED,
            completed_at=timezone.now()
        )
        logger.error('Failed update data: ' + str(e), exc_info=True)
