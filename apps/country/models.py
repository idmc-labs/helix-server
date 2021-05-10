from collections import OrderedDict
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Count
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel, ArchiveAbstractModel
from apps.entry.models import Entry, Figure, FigureCategory
from apps.crisis.models import Crisis
from apps.users.models import User


class GeographicalGroup(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    def __str__(self):
        return self.name


class CountryRegion(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    def __str__(self):
        return self.name


class Country(models.Model):
    GEOJSON_PATH = 'geojsons'

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
            figures_sum='Flow Figures Sum',
            contacts_count='Contacts Count',
            operating_contacts_count='Operating Contacts Count',
        )
        values = CountryFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            crises_count=Count('crises', distinct=True),
            events_count=Count('events', distinct=True),
            entries_count=Count('events__entries', distinct=True),
            figures_count=Count('figures', distinct=True),
            figures_sum=models.Sum(
                'entries__figures__total_figures',
                filter=models.Q(
                    entries__figures__category=FigureCategory.flow_new_displacement_id(),
                    entries__figures__role=Figure.ROLE.RECOMMENDED,
                ),
            ),
            contacts_count=Count('contacts', distinct=True),
            operating_contacts_count=Count('operating_contacts', distinct=True),
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
                                           MinValueValidator(1800, 'Invalid date'),
                                           MaxValueValidator(9999, 'Invalid date'),
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
