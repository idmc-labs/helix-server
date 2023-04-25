import datetime
import logging
from helix.celery import app as celery_app

from django.db.models import (
    Sum, Case, When, IntegerField, Value, F
)
from apps.entry.models import Figure
from apps.event.models import Crisis
from .models import Conflict, Disaster
from .models import StatusLog, DisasterLegacy, ConflictLegacy
from apps.country.models import Country


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
                default=0
            )
        ),
        new_displacement=Sum(
            Case(
                When(
                    category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                    then=F('total_figures')
                ),
                output_field=IntegerField(),
                default=0
            )
        ),
        country=F('country'),
    ).order_by('year')


def update_conflict_and_disaster_data():

    figure_queryset = Figure.objects.filter(
        role=Figure.ROLE.RECOMMENDED
    )
    # Get start year and end year
    start_year = Figure.objects.filter(
        role=Figure.ROLE.RECOMMENDED
    ).order_by('start_date').first().start_date.year
    end_year = Figure.objects.filter(
        role=Figure.ROLE.RECOMMENDED
    ).order_by('-end_date').first().end_date.year

    for year in range(start_year, end_year):
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
        disasters = disaster_qs.annotate(
            new_displacement=Sum(
                Case(
                    When(
                        category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                        then=F('total_figures')
                    ),
                    output_field=IntegerField(),
                    default=0
                )
            ),
            year=Value(year, output_field=IntegerField()),
            hazard_category=F('event__disaster_category__name'),
            hazard_sub_category=F('event__disaster_sub_category__name'),
            hazard_type=F('event__disaster_type__name'),
            hazard_sub_type=F('event__disaster_sub_type__name'),
            iso3=F('country__iso3'),
            country_name=F('country__name'),
            event_name=F('event__name'),
        ).filter(
            new_displacement__isnull=False,
            year__gte=2016,
        ).order_by('year').values(
            'year',
            'event_id',
            'event_name',
            'start_date',
            'start_date_accuracy',
            'end_date',
            'end_date_accuracy',
            'hazard_category',
            'hazard_sub_category',
            'hazard_type',
            'hazard_sub_type',
            'new_displacement',
            'country',
            'iso3',
            'country_name',
        )
        Disaster.objects.bulk_create(
            [
                Disaster(
                    event_id=item['event_id'],
                    event_name=item['event_name'],
                    year=item['year'],
                    start_date=item['start_date'],
                    start_date_accuracy=item['start_date_accuracy'],
                    end_date=item['end_date'],
                    end_date_accuracy=item['end_date_accuracy'],
                    hazard_category=item['hazard_category'],
                    hazard_sub_category=item['hazard_sub_category'],
                    hazard_type=item['hazard_type'],
                    hazard_sub_type=item['hazard_sub_type'],
                    new_displacement=item['new_displacement'],
                    iso3=item['iso3'],
                    country_id=item['country'],
                    country_name=item['country_name'],
                ) for item in disasters
            ]
        )


@celery_app.task
def update_gidd_data(log_id):

    # Delete all the conflicts TODO: Find way to update records
    Conflict.objects.all().delete()

    # Delete disasters
    Disaster.objects.all().delete()

    countries = Country.objects.values('iso3', 'id')

    iso3_to_country_id_map = {country['iso3']: country['id'] for country in countries}

    # Bulk create conflict legacy data
    Conflict.objects.bulk_create(
        [
            Conflict(
                total_displacement=item['total_displacement'],
                new_displacement=item['new_displacement'],
                year=item['year'],
                iso3=item['iso3'],
                country_id=iso3_to_country_id_map[item['iso3']],
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
                hazard_category=item['hazard_category'],
                hazard_sub_category=item['hazard_sub_category'],
                hazard_type=item['hazard_type'],
                hazard_sub_type=item['hazard_sub_type'],
                new_displacement=item['new_displacement'],
                iso3=item['iso3'],
                country_id=iso3_to_country_id_map[item['iso3']],
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
                'new_displacement',
                'iso3',
            )
        ]
    )
    try:
        update_conflict_and_disaster_data()
        StatusLog.objects.filter(id=log_id).update(status=StatusLog.Status.SUCCESS)
        logger.info('Gidd data updated.')
    except Exception as e:
        StatusLog.objects.filter(id=log_id).update(status=StatusLog.Status.FAILED)
        logger.error('Failed update data: ' + str(e))
