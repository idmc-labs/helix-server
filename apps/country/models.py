import typing
from datetime import datetime
from django.db.models.functions import Coalesce

from collections import OrderedDict
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.aggregates.general import StringAgg
from django.db import models
from django.db.models.query import QuerySet
from django.db.models import Count, OuterRef
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel, ArchiveAbstractModel
from apps.entry.models import Entry, Figure
from apps.crisis.models import Crisis
from apps.users.models import User, Portfolio
from apps.users.enums import USER_ROLE
from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR, EXTERNAL_TUPLE_SEPARATOR
from utils.fields import generate_full_media_url


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
            now = timezone.now()
            start_date = datetime(year=now.year, month=1, day=1)
            end_date = now.date()

        return {
            cls.ND_CONFLICT_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        country__region=OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                        event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
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
                        event__event_type=Crisis.CRISIS_TYPE.DISASTER,
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
                        event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
                    ),
                    start_date=start_date,
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
                        event__event_type=Crisis.CRISIS_TYPE.DISASTER,
                    ),
                    start_date=start_date,
                    end_date=end_date,
                ).order_by().values('country__region').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
        }

    def __str__(self):
        return self.name


class MonitoringSubRegion(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    countries: models.QuerySet['Country']

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.country.filters import MonitoringSubRegionFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id='ID',
            name='Region Name',
            regional_coordinator='Regional Coordinator',
            monitoring_expert_count='No. of Monitoring Experts',
            monitoring_experts='Monitoring Experts',
            countries_count='No. of Countries',
            monitored_countries='Monitored Countries',
            unmonitored_countries_count='No. of Unmonitored Countries',
            unmonitored_countries='Unmonitored Countries',
        )

        unmonitored_countries_qs = Country.objects.filter(
            monitoring_sub_region=models.OuterRef('pk'),
        ).exclude(
            portfolio__role=USER_ROLE.MONITORING_EXPERT,
        )

        subregions = MonitoringSubRegionFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            # User stats
            monitoring_experts=StringAgg(
                'portfolios__user__full_name',
                EXTERNAL_TUPLE_SEPARATOR,
                filter=models.Q(portfolios__role=USER_ROLE.MONITORING_EXPERT),
                distinct=True,
            ),
            monitoring_expert_count=Count(
                'portfolios__user',
                filter=models.Q(portfolios__role=USER_ROLE.MONITORING_EXPERT),
                distinct=True,
            ),
            regional_coordinator=StringAgg(
                'portfolios__user__full_name',
                EXTERNAL_TUPLE_SEPARATOR,
                filter=models.Q(portfolios__role=USER_ROLE.REGIONAL_COORDINATOR),
                distinct=True,
            ),
            # Country stats
            countries_count=Count('countries', distinct=True),
            monitored_countries=StringAgg(
                'portfolios__country__idmc_full_name',
                EXTERNAL_TUPLE_SEPARATOR,
                filter=models.Q(portfolios__role=USER_ROLE.MONITORING_EXPERT),
                distinct=True,
            ),
            unmonitored_countries=models.Subquery(
                unmonitored_countries_qs.order_by().values('monitoring_sub_region').annotate(
                    country_names=StringAgg(
                        'idmc_full_name',
                        EXTERNAL_TUPLE_SEPARATOR,
                        distinct=True,
                    ),
                ).values('country_names')[:1],
            ),
            unmonitored_countries_count=Coalesce(models.Subquery(
                unmonitored_countries_qs.order_by().values('monitoring_sub_region').annotate(
                    count=models.Count('id', distinct=True),
                ).values('count')[:1],
            ), 0),
        ).order_by('id')

        return {
            'headers': headers,
            'data': subregions.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': None,
        }

    @property
    def unmonitored_countries_count(self) -> int:
        country_portfolios = Portfolio.objects.filter(
            role=USER_ROLE.MONITORING_EXPERT,
            country__isnull=False,
        ).values_list('country')
        q = self.countries.filter(
            ~models.Q(id__in=country_portfolios)
        )
        return q.count()

    @property
    def unmonitored_countries_names(self) -> str:
        country_portfolios = Portfolio.objects.filter(
            role=USER_ROLE.MONITORING_EXPERT,
            country__isnull=False,
        ).values_list('country')
        q = self.countries.filter(
            ~models.Q(id__in=country_portfolios)
        )
        return EXTERNAL_ARRAY_SEPARATOR.join(q.values_list('idmc_short_name', flat=True))

    @property
    def regional_coordinator(self) -> typing.Optional[Portfolio]:
        if Portfolio.objects.filter(monitoring_sub_region=self,
                                    role=USER_ROLE.REGIONAL_COORDINATOR).exists():
            return Portfolio.objects.get(monitoring_sub_region=self,
                                         role=USER_ROLE.REGIONAL_COORDINATOR)

    @property
    def monitoring_experts_count(self) -> int:
        return Portfolio.objects.filter(
            monitoring_sub_region=self,
            role=USER_ROLE.MONITORING_EXPERT,
        ).values('user').distinct().count()

    def __str__(self):
        return self.name


class CountrySubRegion(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

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
    sub_region = models.ForeignKey('CountrySubRegion', verbose_name=_('Sub Region'), null=True,
                                   related_name='countries', on_delete=models.PROTECT)
    monitoring_sub_region = models.ForeignKey('MonitoringSubRegion', verbose_name=_('Monitoring Sub-Region'), null=True,
                                              related_name='countries', on_delete=models.PROTECT)

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

    contextual_analyses: models.QuerySet['ContextualAnalysis']
    summaries: models.QuerySet['Summary']

    @classmethod
    def _total_figure_disaggregation_subquery(
        cls,
        figures=None,
        ignore_dates=False,
        start_date=None,
        end_date=None,
        year=None
    ):
        '''
        returns the subqueries for figures sum annotations
        '''
        if figures is None:
            figures = Figure.objects.all()
        if start_date is None and end_date is None:
            if year:
                start_date = datetime(year=int(year), month=1, day=1)
                end_date = datetime(year=int(year), month=12, day=31)
            else:
                start_date = datetime(year=timezone.now().year, month=1, day=1)
                end_date = datetime(year=timezone.now().year, month=12, day=31)
        if ignore_dates:
            start_date = None
            end_date = None

        return {
            cls.ND_CONFLICT_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        country=OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                        event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
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
                        event__event_type=Crisis.CRISIS_TYPE.DISASTER,
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
                        event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
                    ),
                    start_date=start_date,
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
                        event__event_type=Crisis.CRISIS_TYPE.DISASTER,
                    ),
                    start_date=start_date,
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

        str_year = filters.get('year', '')
        headers = OrderedDict(
            id='ID',
            geographical_group__name='Geographical group',
            region__name='Region',
            sub_region__name='Sub region',
            name='Name',
            iso2='ISO2',
            iso3='ISO3',
            country_code='Country code',
            idmc_short_name='IDMC short name',
            idmc_full_name='IDMC full name',
            crises_count='Crises count',
            events_count='Events count',
            entries_count='Entries count',
            figures_count='Figures count',
            **{
                cls.IDP_DISASTER_ANNOTATE: f'IDPs disaster figure {str_year}',
                cls.ND_CONFLICT_ANNOTATE: f'ND conflict figure {str_year}',
                cls.IDP_CONFLICT_ANNOTATE: f'IDPs conflict figure {str_year}',
                cls.ND_DISASTER_ANNOTATE: f'ND disaster figure {str_year}',
            }
        )
        data = CountryFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            crises_count=Count('crises', distinct=True),
            events_count=Count('events', distinct=True),
            # NOTE: Subquery was relatively faster than JOINs
            # entries_count=Count('events__entries', distinct=True),
            entries_count=models.Subquery(
                Entry.objects.filter(
                    figures__country=OuterRef('pk')
                ).order_by().values('figures__country').annotate(
                    _count=Count('figures__entry', distinct=True)
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
            # contacts_count=Count('contacts', distinct=True),
            # operating_contacts_count=Count('operating_contacts', distinct=True),
        ).order_by('idmc_short_name')

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': None,
        }

    @classmethod
    def geojson_path(cls, iso3):
        if iso3:
            return f'{cls.GEOJSON_PATH}/{iso3.upper()}.json'

    @classmethod
    def geojson_url(cls, iso3):
        if iso3:
            file_path = f'{cls.GEOJSON_PATH}/{iso3.upper()}.json'
            return generate_full_media_url(file_path)

    @property
    def entries(self) -> QuerySet:
        return Entry.objects.filter(figures__event__countries=self.pk).distinct()

    @property
    def last_contextual_analysis(self):
        return self.contextual_analyses.last()

    @property
    def regional_coordinator(self) -> Portfolio:
        return self.monitoring_sub_region.regional_coordinator

    @property
    def monitoring_expert(self) -> typing.Optional[Portfolio]:
        return Portfolio.objects.filter(
            country=self,
            role=USER_ROLE.MONITORING_EXPERT,
        ).first()

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
                                 verbose_name=_('Cause'),
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

    country_id: int

    class Meta:
        unique_together = (('country', 'year'),)

    def __str__(self):
        return f'PK:{self.pk}-Country-ID:{self.country_id}-Year:{self.year}'
