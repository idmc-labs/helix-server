import datetime
import logging
from helix.celery import app as celery_app
from django.utils import timezone
from django.db import models
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db.models import (
    Sum, Case, When, IntegerField, Value, F, Subquery, OuterRef, Q
)
from django.db.models.functions import Concat
from utils.common import round_and_remove_zero
from apps.entry.models import Figure
from apps.event.models import Crisis
from .models import (
    StatusLog,
    DisasterLegacy,
    ConflictLegacy,
    PublicFigureAnalysis,
    Conflict,
    Disaster,
    DisplacementData,
    IdpsSaddEstimate,
)
from apps.country.models import Country
from apps.report.models import Report
from apps.event.models import EventCode


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
    def get_event_code(event_codes, type=None):
        def _get_event_code_label(key):
            obj = EventCode.EVENT_CODE_TYPE.get(key)
            return getattr(obj, "label", key)

        if not event_codes:
            return

        # FIXME: We also get aggregation when there is not data
        splitted_event_codes = [event_code.split(':') for event_code in event_codes if event_code != ':']

        return ', '.join([
            event_code[0] if type == 'code' else _get_event_code_label(int(event_code[1]))
            for event_code in splitted_event_codes
        ]).split(',')

    figure_queryset = Figure.objects.filter(
        role=Figure.ROLE.RECOMMENDED
    )
    for year in get_gidd_years():
        # FIXME: Check if this should be
        # - Figure.filtered_nd_figures_for_listing
        # - Figure.filtered_idp_figures_for_listing
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
            event_code=ArrayAgg(
                Concat(
                    F('event__event_code__event_code'),
                    Value(':'),
                    F('event__event_code__event_code_type'),
                    Value(':'),
                    F('event__event_code__country__iso3'),
                    output_field=models.CharField(),
                ),
                distinct=True,
                filter=models.Q(event__event_code__country__id=F('country__id')),
            ),
        ).filter(
            year__gte=2016,
        )

        Disaster.objects.bulk_create(
            [
                Disaster(
                    event_id=item['event__id'],
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
                    event_code=get_event_code(item['event_code'], type='code') or [],
                    event_code_type=get_event_code(item['event_code'], type='code_type') or [],
                ) for item in disasters
            ]
        )


def update_public_figure_analysis():
    # NOTE:- Exactly one aggregation should obtained for PFA
    # NOTE:- There must be exaclty one country
    # Delete all the public figure analysis objects
    PublicFigureAnalysis.objects.all().delete()
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
                report=report
            ),
        )

    # Bulk create public analysis
    PublicFigureAnalysis.objects.bulk_create(data)


def update_displacement_data():
    DisplacementData.objects.all().delete()
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


@celery_app.task
def update_gidd_data(log_id):
    # Delete all the conflicts TODO: Find way to update records
    Conflict.objects.all().delete()

    # Delete disasters
    Disaster.objects.all().delete()

    try:
        update_gidd_legacy_data()
        update_conflict_and_disaster_data()
        update_public_figure_analysis()
        update_displacement_data()
        update_idps_sadd_estimates_country_names()
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
