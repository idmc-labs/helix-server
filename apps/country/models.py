from datetime import datetime

from collections import OrderedDict
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Count, OuterRef
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel, ArchiveAbstractModel
from apps.entry.models import Entry, Figure
from apps.crisis.models import Crisis
from apps.users.models import User


class GeographicalGroup(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    def __str__(self):
        return self.name


class CountryRegion(models.Model):
    # NOTE: following are the figure disaggregation fields
    ND_CONFLICT_ANNOTATE = 'total_flow_conflict'
    ND_DISASTER_ANNOTATE = 'total_flow_disaster'
    IDP_CONFLICT_ANNOTATE = 'total_stock_conflict'
    IDP_DISASTER_ANNOTATE = 'total_stock_disaster'

    name = models.CharField(verbose_name=_('Name'), max_length=256)

    @classmethod
    def _total_figure_disaggregation_subquery(
        cls,
        figures=None,
        ignore_dates=False,
    ):
        '''
        returns the subqueries for figures sum annotations
        '''
        figures = figures or Figure.objects.all()
        if ignore_dates:
            start_date = None
            end_date = None
        else:
            start_date = datetime(year=datetime.today().year, month=1, day=1)
            end_date = datetime(year=datetime.today().year, month=12, day=31)
        return {
            cls.ND_CONFLICT_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        country__region=OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                        entry__event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
                    ),
                    # TODO: what about date range
                    start_date=start_date,
                    end_date=end_date
                ).order_by().values('country__region').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            cls.ND_DISASTER_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        country__region=OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                        entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER,
                    ),
                    # TODO: what about date range
                    start_date=start_date,
                    end_date=end_date,
                ).order_by().values('country__region').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            cls.IDP_CONFLICT_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures.filter(
                        country__region=OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                        entry__event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
                    ),
                    end_date=end_date,
                ).order_by().values('country__region').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            cls.IDP_DISASTER_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures.filter(
                        country__region=OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                        entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER,
                    ),
                    end_date=end_date,
                ).order_by().values('country__region').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
        }

    def __str__(self):
        return self.name


class Country(models.Model):
    GEOJSON_PATH = 'geojsons'
    # NOTE: following are the figure disaggregation fields
    ND_CONFLICT_ANNOTATE = 'total_flow_conflict'
    ND_DISASTER_ANNOTATE = 'total_flow_disaster'
    IDP_CONFLICT_ANNOTATE = 'total_stock_conflict'
    IDP_DISASTER_ANNOTATE = 'total_stock_disaster'

    name = models.CharField(verbose_name=_('Name'), max_length=256)
    geographical_group = models.ForeignKey('GeographicalGroup', verbose_name=_('Geographical Group'), null=True,
                                           on_delete=models.SET_NULL)
    region = models.ForeignKey('CountryRegion', verbose_name=_('Region'),
                               related_name='countries', on_delete=models.PROTECT)
    sub_region = models.CharField(verbose_name=_('Sub Region'), max_length=256, null=True)

    iso2 = models.CharField(verbose_name=_('ISO2'), max_length=4,
                            null=True, blank=True)
    iso3 = models.CharField(verbose_name=_('ISO3'), max_length=5,
                            null=True, blank=True)
    country_code = models.PositiveSmallIntegerField(verbose_name=_('Country Code'), null=True, blank=False)
    idmc_short_name = models.CharField(
        verbose_name=_('IDMC Short Name'),
        max_length=256,
        blank=False
    )
    idmc_full_name = models.CharField(verbose_name=_('IDMC Full Name'), max_length=256, null=True, blank=False)
    centroid = ArrayField(verbose_name=_('Centroid'), base_field=models.FloatField(blank=False), null=True)
    bounding_box = ArrayField(verbose_name=_('Bounding Box'),
                              base_field=models.FloatField(blank=False), null=True)
    idmc_short_name_es = models.CharField(verbose_name=_('IDMC Short Name Es'), max_length=256, null=True)
    idmc_short_name_fr = models.CharField(verbose_name=_('IDMC Short Name Fr'), max_length=256, null=True)
    idmc_short_name_ar = models.CharField(verbose_name=_('IDMC Short Name Ar'), max_length=256, null=True)

    @classmethod
    def _total_figure_disaggregation_subquery(
        cls,
        figures=None,
        ignore_dates=False,
    ):
        '''
        returns the subqueries for figures sum annotations
        '''
        figures = figures or Figure.objects.all()
        if ignore_dates:
            start_date = None
            end_date = None
        else:
            start_date = datetime(year=timezone.now().year, month=1, day=1)
            end_date = datetime(year=timezone.now().year, month=12, day=31)
        return {
            cls.ND_CONFLICT_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        country=OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                        entry__event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
                    ),
                    # TODO: what about date range
                    start_date=start_date,
                    end_date=end_date
                ).order_by().values('country').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            cls.ND_DISASTER_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        country=OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                        entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER,
                    ),
                    # TODO: what about date range
                    start_date=start_date,
                    end_date=end_date,
                ).order_by().values('country').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            cls.IDP_CONFLICT_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures.filter(
                        country=OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                        entry__event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
                    ),
                    end_date=end_date,
                ).order_by().values('country').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            cls.IDP_DISASTER_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures.filter(
                        country=OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                        entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER,
                    ),
                    end_date=end_date,
                ).order_by().values('country').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
        }

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.country.filters import CountryFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id='Id',
            name='Name',
            geographical_group__name='Geographical Group',
            region__name='Region',
            sub_region='Sub Region',
            iso2='ISO2',
            iso3='ISO3',
            country_code='Country Code',
            idmc_short_name='IDMC Short Name',
            idmc_full_name='IDMC Full Name',
            crises_count='Crisis Count',
            events_count='Events Count',
            entries_count='Entries Count',
            figures_count='Figures Count',
            **{
                cls.IDP_DISASTER_ANNOTATE: f'IDPs Disaster Figure {timezone.now().year}',
                cls.ND_CONFLICT_ANNOTATE: f'ND Conflict Figure {timezone.now().year}',
                cls.IDP_CONFLICT_ANNOTATE: f'IDPs Conflict Figure {timezone.now().year}',
                cls.ND_DISASTER_ANNOTATE: f'ND Disaster Figure {timezone.now().year}',
            }
        )
        values = CountryFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            crises_count=Count('crises', distinct=True),
            events_count=Count('events', distinct=True),
            # NOTE: Subquery was relatively faster than JOINs
            # entries_count=Count('events__entries', distinct=True),
            entries_count=models.Subquery(
                Entry.objects.filter(
                    event__countries=OuterRef('pk')
                ).order_by().values('event__countries').annotate(
                    _count=Count('pk')
                ).values('_count')[:1],
                output_field=models.IntegerField()
            ),
            figures_count=models.Subquery(
                Figure.objects.filter(
                    country=OuterRef('pk')
                ).order_by().values('country').annotate(
                    _count=Count('pk')
                ).values('_count')[:1],
                output_field=models.IntegerField()
            ),
            contacts_count=Count('contacts', distinct=True),
            operating_contacts_count=Count('operating_contacts', distinct=True),
            **cls._total_figure_disaggregation_subquery(),
        ).select_related(
            'geographical_group', 'region',
        ).values(*[header for header in headers.keys()])
        data = values

        return {
            'headers': headers,
            'data': data,
            'formulae': None,
        }

    @classmethod
    def geojson_path(cls, iso3):
        if iso3:
            return f'{cls.GEOJSON_PATH}/{iso3.upper()}.json'

    @property
    def entries(self):
        return Entry.objects.filter(event__countries=self.id).distinct()

    @property
    def last_contextual_analysis(self):
        return self.contextual_analyses.last()

    @property
    def last_summary(self):
        return self.summaries.last()

    def __str__(self):
        return self.name


class CountryPopulation(models.Model):
    country = models.ForeignKey('Country', verbose_name=_('Country'),
                                related_name='populations', on_delete=models.CASCADE)
    population = models.PositiveIntegerField('Population')
    year = models.PositiveIntegerField('Year',
                                       validators=[
                                           MinValueValidator(1800, 'The date is invalid.'),
                                           MaxValueValidator(9999, 'The date is invalid.'),
                                       ])

    class Meta:
        unique_together = (('country', 'year'),)


class ContextualAnalysis(MetaInformationArchiveAbstractModel, models.Model):
    country = models.ForeignKey('Country', verbose_name=_('Country'),
                                on_delete=models.CASCADE, related_name='contextual_analyses')
    update = models.TextField(verbose_name=_('Update'), blank=False)
    publish_date = models.DateField(verbose_name=_('Published Date'),
                                    blank=True,
                                    null=True)
    crisis_type = enum.EnumField(Crisis.CRISIS_TYPE,
                                 verbose_name=_('Crisis Type'),
                                 blank=True,
                                 null=True)


class Summary(MetaInformationArchiveAbstractModel, models.Model):
    country = models.ForeignKey('Country', verbose_name=_('Country'),
                                on_delete=models.CASCADE, related_name='summaries')
    summary = models.TextField(verbose_name=_('Summary'), blank=False)


class HouseholdSize(ArchiveAbstractModel):
    country = models.ForeignKey('Country',
                                related_name='household_sizes', on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField(verbose_name=_('Year'))
    size = models.FloatField(verbose_name=_('Size'), default=1.0,
                             validators=[
                                 MinValueValidator(0, message="Should be positive")])

    class Meta:
        unique_together = (('country', 'year'),)
