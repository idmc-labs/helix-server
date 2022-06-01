from collections import OrderedDict
from datetime import date
import logging
from typing import Optional
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates.general import ArrayAgg, StringAgg
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.db.models.query import QuerySet
from django.db.models import (
    Sum, Avg, F, Value, Min, Max, Q, Case, When,
)
from django.db.models.functions import Concat, ExtractYear
from django.utils.translation import gettext_lazy as _, gettext
from django.utils import timezone
from django_enumfield import enum
from helix.settings import FIGURE_NUMBER
from apps.contrib.models import (
    MetaInformationAbstractModel,
    UUIDAbstractModel,
    MetaInformationArchiveAbstractModel,
)
from apps.contrib.commons import DATE_ACCURACY
from apps.entry.constants import (
    LESS_THAN_FIVE, FIVE_TO_FOURTEEN, FIFTEEN_TO_TWENTRY_FOUR,
    ZERO_TO_SEVENTEEN, EIGHTEEN_TO_FIFTYNINE, SIXTY_PLUS, OTHER_AGES,
    AGE_CATEGORIES_TO_EXPORT
)
from apps.review.models import Review
from apps.parking_lot.models import ParkedItem
from apps.common.enums import GENDER_TYPE

logger = logging.getLogger(__name__)
User = get_user_model()
CANNOT_UPDATE_MESSAGE = _('You cannot sign off the entry.')


class DisaggregatedAgeCategory(models.Model):
    '''
    Used by disaggregated age data by figure disaggregated_age_json field
    '''
    name = models.CharField(
        verbose_name=_('Name'),
        max_length=256,
        unique=True,
    )
    age_group = models.CharField(
        verbose_name=_('Age Group'),
        max_length=256,
        unique=True,
        null=True,
    )
    age_group_from = models.IntegerField(
        verbose_name=_('Age Group From'),
        null=True
    )
    age_group_to = models.IntegerField(
        verbose_name=_('Age Group To'),
        null=True
    )


class OSMName(UUIDAbstractModel, models.Model):
    class OSM_ACCURACY(enum.Enum):
        ADM0 = 0
        ADM1 = 1
        ADM2 = 2
        ADM3 = 3
        POINT = 4

        __labels__ = {
            ADM0: _('Country/territory (ADM0)'),
            ADM1: _('State/Region/Province (ADM1)'),
            ADM2: _('District/Zone/Department (ADM2)'),
            ADM3: _('County/City/Town/Village/Woreda (ADM3)'),
            POINT: _('Point'),
        }

    class IDENTIFIER(enum.Enum):
        ORIGIN = 0
        DESTINATION = 1

        __labels__ = {
            ORIGIN: _('Origin'),
            DESTINATION: _('Destination'),
        }

    # default unique behaviour is removed
    uuid = models.UUIDField(verbose_name='UUID',
                            blank=True, default=uuid4)
    # external API fields
    wikipedia = models.TextField(verbose_name=_('Wikipedia'),
                                 blank=True,
                                 null=True)
    rank = models.IntegerField(verbose_name=_('Rank'),
                               blank=True,
                               null=True)
    country = models.TextField(verbose_name=_('Country'))
    # NOTE: country-code here actually stores iso2
    country_code = models.CharField(verbose_name=_('Country Code'), max_length=8,
                                    null=True, blank=False)
    street = models.TextField(verbose_name=_('Street'),
                              blank=True,
                              null=True)
    wiki_data = models.TextField(verbose_name=_('Wiki data'),
                                 blank=True,
                                 null=True)
    osm_id = models.CharField(verbose_name=_('OSM Id'), max_length=256)
    osm_type = models.CharField(verbose_name=_('OSM Type'), max_length=256)
    house_numbers = models.TextField(verbose_name=_('House numbers'),
                                     blank=True,
                                     null=True)
    identifier = enum.EnumField(verbose_name=_('Identifier'), enum=IDENTIFIER)
    city = models.CharField(verbose_name=_('City'), max_length=256,
                            blank=True,
                            null=True)
    display_name = models.CharField(verbose_name=_('Display name'), max_length=512)
    lon = models.FloatField(verbose_name=_('Longitude'))
    lat = models.FloatField(verbose_name=_('Latitude'))
    state = models.TextField(verbose_name=_('State'),
                             blank=True, null=True)
    bounding_box = ArrayField(verbose_name=_('Bounding Box'),
                              base_field=models.FloatField(),
                              blank=True, null=True)
    type = models.TextField(verbose_name=_('Type'),
                            blank=True, null=True)
    importance = models.FloatField(verbose_name=_('Importance'),
                                   blank=True, null=True)
    class_name = models.TextField(verbose_name=_('Class'),
                                  blank=True, null=True)
    name = models.TextField(verbose_name=_('Name'))
    name_suffix = models.TextField(verbose_name=_('Name Suffix'),
                                   blank=True, null=True)
    place_rank = models.IntegerField(verbose_name=_('Place Rank'),
                                     blank=True, null=True)
    alternative_names = models.TextField(verbose_name=_('Alternative names'),
                                         blank=True, null=True)
    # custom fields
    accuracy = enum.EnumField(verbose_name=_('Accuracy'),
                              enum=OSM_ACCURACY)
    moved = models.BooleanField(verbose_name=_('Moved'),
                                default=False)


class FigureDisaggregationAbstractModel(models.Model):
    class DISPLACEMENT_TYPE(enum.Enum):
        RURAL = 0
        URBAN = 1

        __labels__ = {
            RURAL: _("Rural"),
            URBAN: _("Urban"),
        }

    # disaggregation information
    disaggregation_displacement_urban = models.PositiveIntegerField(
        verbose_name=_('Displacement/Urban'),
        blank=True,
        null=True
    )
    disaggregation_displacement_rural = models.PositiveIntegerField(
        verbose_name=_('Displacement/Rural'),
        blank=True,
        null=True
    )
    disaggregation_location_camp = models.PositiveIntegerField(
        verbose_name=_('Location/Camp'),
        blank=True,
        null=True
    )
    disaggregation_location_non_camp = models.PositiveIntegerField(
        verbose_name=_('Location/Non-Camp'),
        blank=True,
        null=True
    )
    # lesbian, gay, bisexual, transgender, intersex, and questioning (LGBTIQ)
    disaggregation_lgbtiq = models.PositiveIntegerField(
        verbose_name=_('LGBTIQ+'),
        blank=True,
        null=True
    )
    disaggregation_disability = models.PositiveIntegerField(
        verbose_name=_('Disability'),
        blank=True,
        null=True
    )
    disaggregation_indigenous_people = models.PositiveIntegerField(
        verbose_name=_('Indigenous people'),
        blank=True,
        null=True
    )
    disaggregation_sex_male = models.PositiveIntegerField(
        verbose_name=_('Sex/Male'),
        blank=True,
        null=True
    )
    disaggregation_sex_female = models.PositiveIntegerField(
        verbose_name=_('Sex/Female'),
        blank=True,
        null=True
    )
    disaggregation_age = models.ManyToManyField(
        'entry.DisaggregatedAge',
        verbose_name=_('Disaggregated age'),
        blank=True,
        related_name='%(app_label)s_%(class)s_related'
    )
    disaggregation_strata_json = ArrayField(
        base_field=JSONField(verbose_name=_('Stratum')),
        verbose_name=_('Strata Disaggregation'),
        blank=True,
        null=True)
    # conflict based disaggregation
    disaggregation_conflict = models.PositiveIntegerField(
        verbose_name=_('Conflict/Conflict'),
        blank=True,
        null=True
    )
    disaggregation_conflict_political = models.PositiveIntegerField(
        verbose_name=_('Conflict/Violence-Political'),
        blank=True,
        null=True
    )
    disaggregation_conflict_criminal = models.PositiveIntegerField(
        verbose_name=_('Conflict/Violence-Criminal'),
        blank=True,
        null=True
    )
    disaggregation_conflict_communal = models.PositiveIntegerField(
        verbose_name=_('Conflict/Violence-Communal'),
        blank=True,
        null=True
    )
    disaggregation_conflict_other = models.PositiveIntegerField(
        verbose_name=_('Other'),
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


class DisaggregatedAge(models.Model):
    sex = enum.EnumField(enum=GENDER_TYPE, verbose_name=_('Sex'))
    uuid = models.UUIDField(verbose_name='UUID', blank=True, default=uuid4)
    value = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Value'))
    category = models.ForeignKey(
        'entry.DisaggregatedAgeCategory', related_name='disaggregated_age_category', on_delete=models.PROTECT, blank=False,
        null=True, verbose_name=_('Disaggregated age category')
    )

    def __str__(self):
        return str(self.id)


class Figure(MetaInformationArchiveAbstractModel,
             UUIDAbstractModel,
             FigureDisaggregationAbstractModel,
             models.Model):
    from apps.crisis.models import Crisis

    class QUANTIFIER(enum.Enum):
        MORE_THAN = 0
        LESS_THAN = 1
        EXACT = 2
        APPROXIMATELY = 3

        __labels__ = {
            MORE_THAN: _("More than"),
            LESS_THAN: _("Less than"),
            EXACT: _("Exact"),
            APPROXIMATELY: _("Approximately"),
        }

    class UNIT(enum.Enum):
        PERSON = 0
        HOUSEHOLD = 1

        __labels__ = {
            PERSON: _("Person"),
            HOUSEHOLD: _("Household"),
        }

    class ROLE(enum.Enum):
        RECOMMENDED = 0
        TRIANGULATION = 1

        __labels__ = {
            RECOMMENDED: _("Recommended figure"),
            TRIANGULATION: _("Triangulation"),
        }

    class DISPLACEMENT_OCCURRED(enum.Enum):
        BEFORE = 0
        DURING = 1
        AFTER = 2
        UNKNOWN = 3

        __labels__ = {
            BEFORE: _('Before'),
            AFTER: _('After'),
            DURING: _('During'),
            UNKNOWN: _('Unknown'),
        }

    class FIGURE_CATEGORY_TYPES(enum.Enum):
        IDPS = 0
        RETURNEES = 1
        RETURN = 2
        LOCALLY_INTEGRATED_IDPS = 3
        IDPS_SETTLED_ELSEWHERE = 4
        PEOPLE_DISPLACED_ACROSS_BORDERS = 5
        NEW_DISPLACEMENT = 6
        MULTIPLE_DISPLACEMENT = 7
        PARTIAL_STOCK = 8
        PARTIAL_FLOW = 9
        CROSS_BORDER_FLIGHT = 10
        CROSS_BORDER_RETURN = 11
        RELOCATION_ELSEWHERE = 12
        DEATHS = 13
        PROVISIONAL_SOLUTIONS = 14
        FAILED_LOCAL_INTEGRATION = 15
        LOCAL_INTEGRATION = 16
        FAILED_RETURN_RETURNEE_DISPLACEMENT = 17
        UNVERIFIED_STOCK = 18
        UNVERIFIED_FLOW = 19
        BIRTH = 20
        FAILED_RELOCATION_ELSEWHERE = 21

        __labels__ = {
            IDPS: _('IDPs'),
            RETURNEES: _('Returnees'),
            RETURN: _('Return'),
            LOCALLY_INTEGRATED_IDPS: _('Locally Integrated IDPs'),
            IDPS_SETTLED_ELSEWHERE: _('IDPs Settled Elsewhere'),
            PEOPLE_DISPLACED_ACROSS_BORDERS: _('People displaced across borders'),
            NEW_DISPLACEMENT: _('New Displacement'),
            MULTIPLE_DISPLACEMENT: _('Multiple Displacement'),
            PARTIAL_STOCK: _('Partial stock'),
            PARTIAL_FLOW: _('Partial flow'),
            CROSS_BORDER_FLIGHT: _('Cross-border Flight'),
            CROSS_BORDER_RETURN: _('Cross-border Return'),
            RELOCATION_ELSEWHERE: _('Relocation Elsewhere'),
            DEATHS: _('Deaths'),
            PROVISIONAL_SOLUTIONS: _('Provisional Solutions'),
            FAILED_LOCAL_INTEGRATION: _('Failed Local Integration'),
            LOCAL_INTEGRATION: _('Local Integration'),
            FAILED_RETURN_RETURNEE_DISPLACEMENT: _('Failed Return / Returnee Displacement'),
            UNVERIFIED_STOCK: _('Unverified stock'),
            UNVERIFIED_FLOW: _('Unverified flow'),
            BIRTH: _('Birth'),
            FAILED_RELOCATION_ELSEWHERE: _('Failed relocation elsewhere')

        }

    class FIGURE_TERMS(enum.Enum):
        EVACUATED = 0
        DISPLACED = 1
        FORCED_TO_FLEE = 2
        RELOCATED = 3
        SHELTERED = 4
        IN_RELIEF_CAMP = 5
        DESTROYED_HOUSING = 6
        PARTIALLY_DESTROYED_HOUSING = 7
        UNINHABITABLE_HOUSING = 8
        HOMELESS = 9
        AFFECTED = 10
        RETURNS = 11
        MULTIPLE_OR_OTHER = 12

        __labels__ = {
            EVACUATED: _('Evacuated'),
            DISPLACED: _('Displaced'),
            FORCED_TO_FLEE: _('Forced to flee'),
            RELOCATED: _('Relocated'),
            SHELTERED: _('Sheltered'),
            IN_RELIEF_CAMP: _('In relief camp'),
            DESTROYED_HOUSING: _('Destroyed housing'),
            PARTIALLY_DESTROYED_HOUSING: _('Partially destroyed housing'),
            UNINHABITABLE_HOUSING: _('Uninhabitable housing'),
            HOMELESS: _('Homeless'),
            AFFECTED: _('Affected'),
            RETURNS: _('Returns'),
            MULTIPLE_OR_OTHER: _('Multiple/Other'),
        }

    uuid = models.UUIDField(verbose_name='UUID',
                            blank=True, default=uuid4)
    entry = models.ForeignKey('Entry', verbose_name=_('Entry'),
                              related_name='figures', on_delete=models.CASCADE)
    # to keep track of the old sub facts
    was_subfact = models.BooleanField(default=False)
    quantifier = enum.EnumField(enum=QUANTIFIER, verbose_name=_('Quantifier'))
    reported = models.PositiveIntegerField(verbose_name=_('Reported Figures'))
    unit = enum.EnumField(enum=UNIT, verbose_name=_('Unit of Figure'), default=UNIT.PERSON)
    household_size = models.FloatField(
        verbose_name=_('Household Size'),
        blank=True, null=True
    )
    total_figures = models.PositiveIntegerField(verbose_name=_('Total Figures'), default=0,
                                                editable=False)
    category = enum.EnumField(
        enum=FIGURE_CATEGORY_TYPES,
        verbose_name=_('Figure Category'),
        blank=True, null=True
    )
    term = enum.EnumField(
        enum=FIGURE_TERMS,
        verbose_name=_('Figure Term'),
        blank=True, null=True
    )
    displacement_occurred = enum.EnumField(
        enum=DISPLACEMENT_OCCURRED,
        verbose_name=_('Displacement Occurred'),
        null=True,
        blank=True,
    )
    role = enum.EnumField(enum=ROLE, verbose_name=_('Role'), default=ROLE.RECOMMENDED)

    # start date is stock reporting date for stock figures
    start_date = models.DateField(verbose_name=_('Start Date'),
                                  blank=False, null=True,
                                  db_index=True)
    start_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('Start Date Accuracy'),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    # end date is expiry date for stock figures
    end_date = models.DateField(verbose_name=_('End Date'),
                                blank=True, null=True)
    end_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('End date accuracy'),
        blank=True,
        null=True,
    )
    include_idu = models.BooleanField(verbose_name=_('Include in IDU'))
    excerpt_idu = models.TextField(verbose_name=_('Excerpt for IDU'),
                                   blank=True, null=True)

    country = models.ForeignKey('country.Country', verbose_name=_('Country'),
                                blank=True, null=True,
                                related_name='figures', on_delete=models.SET_NULL)

    is_disaggregated = models.BooleanField(verbose_name=_('Is disaggregated'),
                                           default=False)
    is_housing_destruction = models.BooleanField(
        verbose_name=_('Housing destruction (recommended estimate for this entry)'),
        null=True,
        blank=True,
    )

    # locations
    geo_locations = models.ManyToManyField('OSMName', verbose_name=_('Geo Locations'),
                                           related_name='figures')

    calculation_logic = models.TextField(verbose_name=_('Analysis and Calculation Logic'),
                                         blank=True, null=True)
    tags = models.ManyToManyField('FigureTag', blank=True)
    source_excerpt = models.TextField(verbose_name=_('Excerpt from Source'),
                                      blank=True, null=True)
    event = models.ForeignKey(
        'event.Event', verbose_name=_('Event'),
        related_name='figures', on_delete=models.CASCADE
    )
    context_of_violence = models.ManyToManyField(
        'event.ContextOfViolence', verbose_name=_('Context of violence'), blank=True, related_name='figures'
    )
    figure_cause = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Figure Cause'))
    violence = models.ForeignKey(
        'event.Violence', verbose_name=_('Figure Violence'),
        blank=False, null=True,
        related_name='figures', on_delete=models.SET_NULL
    )
    violence_sub_type = models.ForeignKey(
        'event.ViolenceSubType', verbose_name=_('Figure Violence Sub Type'),
        blank=True, null=True,
        related_name='figures', on_delete=models.SET_NULL
    )
    disaster_category = models.ForeignKey(
        'event.DisasterCategory', verbose_name=_('Figure Disaster Category'),
        blank=True, null=True,
        related_name='figures', on_delete=models.SET_NULL
    )
    disaster_sub_category = models.ForeignKey(
        'event.DisasterSubCategory', verbose_name=_('Figure Disaster Sub Category'),
        blank=True, null=True,
        related_name='figures', on_delete=models.SET_NULL
    )
    disaster_type = models.ForeignKey(
        'event.DisasterType', verbose_name=_('Figure Disaster Type'),
        blank=True, null=True,
        related_name='figures', on_delete=models.SET_NULL
    )
    disaster_sub_type = models.ForeignKey(
        'event.DisasterSubType', verbose_name=_('Figure Disaster Sub Type'),
        blank=True, null=True,
        related_name='figures', on_delete=models.SET_NULL
    )
    other_sub_type = models.ForeignKey(
        'event.OtherSubType', verbose_name=_('Other sub type'),
        blank=True, null=True,
        related_name='figures', on_delete=models.SET_NULL)
    osv_sub_type = models.ForeignKey(
        'event.OsvSubType', verbose_name=_('Figure OSV sub type'),
        blank=True, null=True, related_name='figures',
        on_delete=models.SET_NULL
    )

    class Meta:
        indexes = [
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
            models.Index(fields=['country']),
            models.Index(fields=['category']),
            models.Index(fields=['role']),
            models.Index(fields=['event']),
        ]

    # methods
    @classmethod
    def filtered_nd_figures(
        cls,
        qs: QuerySet,
        start_date: Optional[date],
        end_date: Optional[date] = None,
    ):
        end_date = end_date or timezone.now().date()
        qs = qs.filter(
            Q(
                end_date__isnull=True,
            ) | Q(
                end_date__isnull=False,
                end_date__lte=end_date,
            ),
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
        )
        if start_date:
            qs = qs.filter(
                end_date__gte=start_date,
            )
        return qs

    @classmethod
    def stock_list(cls):
        return [
            Figure.FIGURE_CATEGORY_TYPES.IDPS.value,
            Figure.FIGURE_CATEGORY_TYPES.RETURNEES.value,
            Figure.FIGURE_CATEGORY_TYPES.LOCALLY_INTEGRATED_IDPS.value,
            Figure.FIGURE_CATEGORY_TYPES.IDPS_SETTLED_ELSEWHERE.value,
            Figure.FIGURE_CATEGORY_TYPES.PEOPLE_DISPLACED_ACROSS_BORDERS.value,
            Figure.FIGURE_CATEGORY_TYPES.PARTIAL_STOCK.value,
            Figure.FIGURE_CATEGORY_TYPES.UNVERIFIED_STOCK.value
        ]

    @classmethod
    def flow_list(cls):
        return [
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
            Figure.FIGURE_CATEGORY_TYPES.MULTIPLE_DISPLACEMENT.value,
            Figure.FIGURE_CATEGORY_TYPES.PARTIAL_FLOW.value,
            Figure.FIGURE_CATEGORY_TYPES.CROSS_BORDER_FLIGHT.value,
            Figure.FIGURE_CATEGORY_TYPES.CROSS_BORDER_RETURN.value,
            Figure.FIGURE_CATEGORY_TYPES.RELOCATION_ELSEWHERE.value,
            Figure.FIGURE_CATEGORY_TYPES.DEATHS.value,
            Figure.FIGURE_CATEGORY_TYPES.PROVISIONAL_SOLUTIONS.value,
            Figure.FIGURE_CATEGORY_TYPES.FAILED_LOCAL_INTEGRATION.value,
            Figure.FIGURE_CATEGORY_TYPES.LOCAL_INTEGRATION.value,
            Figure.FIGURE_CATEGORY_TYPES.FAILED_RETURN_RETURNEE_DISPLACEMENT.value,
            Figure.FIGURE_CATEGORY_TYPES.UNVERIFIED_FLOW.value,
        ]

    @classmethod
    def displacement_occur_list(cls):
        return [
            Figure.FIGURE_TERMS.EVACUATED.value,
            Figure.FIGURE_TERMS.DISPLACED.value,
            Figure.FIGURE_TERMS.FORCED_TO_FLEE.value,
            Figure.FIGURE_TERMS.RELOCATED.value,
            Figure.FIGURE_TERMS.SHELTERED.value,
            Figure.FIGURE_TERMS.IN_RELIEF_CAMP.value,
        ]

    @classmethod
    def housing_list(cls):
        return [
            Figure.FIGURE_TERMS.DESTROYED_HOUSING.value,
            Figure.FIGURE_TERMS.PARTIALLY_DESTROYED_HOUSING.value,
            Figure.FIGURE_TERMS.UNINHABITABLE_HOUSING.value,
        ]

    @classmethod
    def filtered_idp_figures(
        cls,
        qs: QuerySet,
        reference_point: Optional[date] = None,
    ):
        reference_point = reference_point or timezone.now().date()
        return qs.filter(
            Q(
                # if end date does not exist, we must make sure that that figure started before given start date
                end_date__isnull=True
            ) | Q(
                # if end date exists (=expired), we must make sure that expiry date is after the given end date,
                # also figure started before the end date
                end_date__isnull=False,
                end_date__gte=reference_point,
            ),
            start_date__isnull=False,
            start_date__lte=reference_point,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS.value
        )

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.extraction.filters import FigureExtractionFilterSet

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        qs = FigureExtractionFilterSet(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs
        return cls.get_figure_excel_sheets_data(qs)

    @classmethod
    def get_figure_excel_sheets_data(cls, figures):
        from apps.crisis.models import Crisis
        headers = OrderedDict(
            old_id='Old Id',
            id='Id',
            created_at='Created at',
            created_by__full_name='Created by',
            entry_id='Entry Id',
            entry__old_id='Entry Old Id',
            quantifier='Quantifier',
            reported='Reported',
            unit='Unit',
            household_size='Household Size',
            total_figures='Total Figures',
            category='Figure Category',
            term='Figure Term',
            displacement_occurred='Displacement Occurred',
            role='Figure Role',
            year='Year',
            start_date='Start Date',
            start_date_accuracy='Start Date Accuracy',
            end_date='End Date',
            end_date_accuracy='End Date Accuracy',
            country__iso3='ISO3',
            country__name='Country',
            country__region__name='Region',
            centroid_lat='Centroid Lat',
            centroid_lon='Centroid Lon',
            centroid='Centroid',
            geolocations='Geolocations (City)',
            include_idu='Include in IDU',
            excerpt_idu='Excerpt IDU',
            publishers_name='Publishers',
            is_housing_destruction='Is housing destruction',
            tags__name='Tags',
            calculation_logic='Analysis and Calculation Logic',
            source_excerpt='Source Excerpt',
            geo_locations__identifier='Type of point',
            disaggregation_displacement_urban='Displacement: Urban',
            disaggregation_displacement_rural='Displacement: Rural',
            disaggregation_location_camp='Location: Camp',
            disaggregation_location_non_camp='Location: Non-Camp',
            disaggregation_disability='Disability',
            disaggregation_indigenous_people='Indigenous People',
            total_female_age_group_less_than_five='F_<5',
            total_female_age_group_five_to_forteen='F_5-14',
            total_female_age_group_fifteen_to_twenty_four="F_15-24",
            total_female_age_group_zero_to_seventeen="F_0-17",
            total_female_age_group_eighteen_to_fiftynine="F_18-59",
            total_female_age_group_sixty_plus="F_60+",
            total_other_age_group_female="F_other age group",
            total_male_age_group_less_than_five='M_<5',
            total_male_age_group_five_to_forteen='M_5-14',
            total_male_age_group_fifteen_to_twenty_four="M_15-24",
            total_male_age_group_zero_to_seventeen="M_0-17",
            total_male_age_group_eighteen_to_fiftynine="M_18-59",
            total_male_age_group_sixty_plus="M_60+",
            total_other_age_group_male="M_other age group",
            entry__url='Link',
            entry__article_title='Event Title',
            event__crisis_id='Crisis Id',
            event__id='Event Id',
            event__old_id='Event Old Id',
            event__crisis__name='Crisis Name',
            event__name='Event Name',
            event__start_date='Event Start Date',
            event__event_type='Event Cause',
            event__other_sub_type__name='Other Event Sub Type',
            event__violence__name='Violence',
            event__violence_sub_type__name='Violence Sub Type',
            event__osv_sub_type__name="OSV Sub Type",
            event__disaster_category__name='Disaster Category',
            event__disaster_sub_category__name='Disaster Sub Category',
            event__disaster_type__name='Disaster Type',
            event__disaster_sub_type__name='Disaster Sub Type',
            context_of_violence__name='Context of violences',
        )
        values = figures.order_by(
            '-created_at'
        ).annotate(
            centroid_lat=Avg('geo_locations__lat'),
            centroid_lon=Avg('geo_locations__lon'),
            geolocations=StringAgg(
                'geo_locations__city',
                delimiter='; ',
                filter=~Q(
                    Q(geo_locations__city__isnull=True) | Q(geo_locations__city='')
                ),
                distinct=True
            ),
            publishers_name=StringAgg(
                'entry__publishers__name',
                delimiter='; ',
                filter=~Q(entry__publishers__name=''),
                distinct=True
            ),
            year=ExtractYear("start_date")
        ).annotate(
            centroid=models.Case(
                models.When(
                    centroid_lat__isnull=False,
                    then=Concat(
                        F('centroid_lat'), Value(', '), F('centroid_lon'),
                        output_field=models.CharField()
                    )
                ),
                default=Value('')
            )
        ).annotate(
            total_female_age_group_less_than_five=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[LESS_THAN_FIVE]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_female_age_group_five_to_forteen=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[FIVE_TO_FOURTEEN]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_female_age_group_fifteen_to_twenty_four=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[FIFTEEN_TO_TWENTRY_FOUR]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_female_age_group_zero_to_seventeen=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[ZERO_TO_SEVENTEEN]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_female_age_group_eighteen_to_fiftynine=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[EIGHTEEN_TO_FIFTYNINE]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_female_age_group_sixty_plus=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[SIXTY_PLUS]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_other_age_group_female=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[OTHER_AGES]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_less_than_five=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[LESS_THAN_FIVE]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_five_to_forteen=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[FIVE_TO_FOURTEEN]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_fifteen_to_twenty_four=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[FIFTEEN_TO_TWENTRY_FOUR]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_zero_to_seventeen=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[ZERO_TO_SEVENTEEN]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_eighteen_to_fiftynine=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[EIGHTEEN_TO_FIFTYNINE]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_sixty_plus=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[SIXTY_PLUS]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_other_age_group_male=Sum(
                Case(When(
                    Q(
                        disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[OTHER_AGES]
                    ), then='disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            )
        ).select_related(
            'entry',
            'event',
            'category',
            'term',
            'created_by',
        ).prefetch_related(
            'geo_locations',
            'disaggregation_age',
            'disaggregation_age__category',
            'geo_locations__identifier',
            'context_of_violence'
        ).order_by(
            '-entry',
            '-created_at',
        ).values(*[header for header in headers.keys()])

        def transformer(datum):
            return {
                **datum,
                'include_idu': 'Yes' if datum['include_idu'] else 'No',
                'start_date_accuracy': getattr(DATE_ACCURACY.get(datum['start_date_accuracy']), 'name', ''),
                'end_date_accuracy': getattr(DATE_ACCURACY.get(datum['end_date_accuracy']), 'name', ''),
                'quantifier': getattr(Figure.QUANTIFIER.get(datum['quantifier']), 'name', ''),
                'unit': getattr(Figure.UNIT.get(datum['unit']), 'name', ''),
                'role': getattr(Figure.ROLE.get(datum['role']), 'name', ''),
                'displacement_occurred': getattr(
                    Figure.DISPLACEMENT_OCCURRED.get(datum['displacement_occurred']), 'name', ''
                ),
                'event__event_type': getattr(Crisis.CRISIS_TYPE.get(
                    datum['event__event_type']), 'name', ''
                ),
                'geo_locations__identifier': getattr(OSMName.IDENTIFIER.get(
                    datum['geo_locations__identifier']), 'name', ''
                ),
            }

        return {
            'headers': headers,
            'data': values,
            'formulae': None,
            'transformer': transformer,
        }

    @classmethod
    def get_total_stock_idp_figure(cls, filters):
        from apps.extraction.filters import FigureExtractionFilterSet
        return FigureExtractionFilterSet(data=filters or dict(), queryset=cls.objects.all()).qs.filter(
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS.value
        ).aggregate(total=Sum('total_figures'))['total']

    @classmethod
    def get_total_flow_nd_figure(cls, filters):
        from apps.extraction.filters import FigureExtractionFilterSet
        return FigureExtractionFilterSet(data=filters or dict(), queryset=cls.objects.all()).qs.filter(
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value
        ).aggregate(total=Sum('total_figures'))['total']

    @classmethod
    def can_be_created_by(cls, user: User, entry: 'Entry') -> bool:
        return entry.can_be_updated_by(user)

    def can_be_updated_by(self, user: User) -> bool:
        """
        used to check before deleting as well
        """
        return self.entry.can_be_updated_by(user)

    @staticmethod
    def clean_idu(values: dict, instance=None) -> OrderedDict:
        errors = OrderedDict()
        if values.get('include_idu', getattr(instance, 'include_idu', None)):
            excerpt_idu = values.get('excerpt_idu', getattr(instance, 'excerpt_idu', None))
            if excerpt_idu is None or not excerpt_idu.strip():
                errors['excerpt_idu'] = gettext('This field is required.')
        return errors

    # core

    def save(self, *args, **kwargs):
        # TODO: set household size from the country
        self.total_figures = self.reported
        if self.unit == self.UNIT.HOUSEHOLD:
            self.total_figures = self.reported * self.household_size
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.quantifier.label} {self.reported}'


class FigureTag(MetaInformationAbstractModel):
    name = models.CharField(verbose_name=_('Name'), max_length=256)


class EntryReviewer(MetaInformationAbstractModel, models.Model):
    class CannotUpdateStatusException(Exception):
        message = CANNOT_UPDATE_MESSAGE

    class REVIEW_STATUS(enum.Enum):
        # NOTE: Values of each name contains its significance, and is used elsewhere for comparison
        TO_BE_REVIEWED = 0
        UNDER_REVIEW = 1
        REVIEW_COMPLETED = 2
        SIGNED_OFF = 3

        __labels__ = {
            UNDER_REVIEW: _("Under Review"),
            REVIEW_COMPLETED: _("Review Completed"),
            SIGNED_OFF: _("Signed Off"),
            TO_BE_REVIEWED: _("To be reviewed"),
        }

    entry = models.ForeignKey('Entry', verbose_name=_('Entry'),
                              related_name='reviewing', on_delete=models.CASCADE)
    reviewer = models.ForeignKey('users.User', verbose_name=_('Reviewer'),
                                 related_name='reviewing', on_delete=models.CASCADE)
    status = enum.EnumField(enum=REVIEW_STATUS, verbose_name=_('Review Status'),
                            default=REVIEW_STATUS.TO_BE_REVIEWED)

    def __str__(self):
        return f'{self.entry_id} {self.reviewer} {self.status}'

    @classmethod
    def assign_creator(cls, entry: 'Entry', user: 'User') -> None:
        cls.objects.filter(
            entry=entry,
            created_by__isnull=True
        ).update(created_by=user)

    def update_status(self, status: REVIEW_STATUS) -> None:
        if status == self.REVIEW_STATUS.SIGNED_OFF \
                and not self.reviewer.has_perms(('entry.sign_off_entry',)):
            raise self.CannotUpdateStatusException()
        self.status = status

    def save(self, *args, **kwargs):
        self.update_status(self.status)
        return super().save(*args, **kwargs)


class Entry(MetaInformationArchiveAbstractModel, models.Model):
    FIGURES_PER_ENTRY = FIGURE_NUMBER

    # NOTE figure disaggregation variable definitions
    ND_FIGURES_ANNOTATE = 'total_flow_nd_figures'
    IDP_FIGURES_ANNOTATE = 'total_stock_idp_figures'

    url = models.URLField(verbose_name=_('Source URL'), max_length=2000,
                          blank=True, null=True)
    associated_parked_item = models.OneToOneField('parking_lot.ParkedItem',
                                                  blank=True, null=True,
                                                  on_delete=models.SET_NULL, related_name='entry')
    preview = models.ForeignKey('contrib.SourcePreview',
                                related_name='entry', on_delete=models.SET_NULL,
                                blank=True, null=True,
                                help_text=_('After the preview has been generated pass its id'
                                            ' along during entry creation, so that during entry '
                                            'update the preview can be obtained.'))
    document = models.ForeignKey('contrib.Attachment', verbose_name='Attachment',
                                 on_delete=models.CASCADE, related_name='+',
                                 null=True, blank=True)
    document_url = models.URLField(verbose_name=_('Document URL'), max_length=2000,
                                   blank=True, null=True)
    article_title = models.TextField(verbose_name=_('Event Title'))
    sources = models.ManyToManyField('organization.Organization', verbose_name=_('Source'),
                                     blank=True, related_name='sourced_entries')
    publishers = models.ManyToManyField('organization.Organization', verbose_name=_('Publisher'),
                                        blank=True, related_name='published_entries')
    publish_date = models.DateField(verbose_name=_('Published Date'))

    idmc_analysis = models.TextField(verbose_name=_('Trends and patterns of displacement to be highlighted'),
                                     blank=True, null=True)
    is_confidential = models.BooleanField(
        verbose_name=_('Confidential Source'),
        default=False,
    )
    reviewers = models.ManyToManyField('users.User', verbose_name=_('Reviewers'),
                                       blank=True,
                                       related_name='review_entries',
                                       through='EntryReviewer',
                                       through_fields=('entry', 'reviewer'))
    review_status = enum.EnumField(enum=EntryReviewer.REVIEW_STATUS, verbose_name=_('Review Status'),
                                   null=True, blank=True)

    @classmethod
    def _total_figure_disaggregation_subquery(cls, figures=None):
        figures1 = figures or Figure.objects.all()
        figures2 = figures or Figure.objects.all()
        return {
            cls.ND_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures1.filter(
                        entry=models.OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    start_date=None,
                    end_date=None,
                ).order_by().values('entry').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            cls.IDP_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures2.filter(
                        entry=models.OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    reference_point=timezone.now().date(),
                ).order_by().values('entry').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
        }

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.extraction.filters import EntryExtractionFilterSet

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            old_id='Old Id',
            id='Id',
            created_at='Created at',
            created_by__full_name='Created by',
            article_title='Entry Title',
            url='URL',
            is_confidential='Confidential',
            publish_date='Publish Date',
            document__attachment='Document',
            document__mimetype='Filetype',
            document__filetype_detail='Filetype Detail',
            sources_name='Sources',
            source_types='Source Types',
            publishers_name='Publishers',
            publisher_types='Publisher Types',
            idmc_analysis='Trends and patterns of displacement to be highlighted',
            countries='Countries Affected',
            countries_iso3='ISO3s Affected',
            centroid_lat='Centroid Lat',
            centroid_lon='Centroid Lon',
            centroid='Centroid',
            categories='Figure Categories',
            terms='Figure Terms',
            figures_count='Figures Count',
            **{
                cls.IDP_FIGURES_ANNOTATE: 'IDPs Figure',
                cls.ND_FIGURES_ANNOTATE: 'ND Figure',
            },
            min_fig_start='Earliest figure start',
            max_fig_start='Latest figure start',
            min_fig_end='Earliest figure end',
            max_fig_end='Latest figure end',
            total_female_age_group_less_than_five='F_<5',
            total_female_age_group_five_to_forteen='F_5-14',
            total_female_age_group_fifteen_to_twenty_four="F_15-24",
            total_female_age_group_zero_to_seventeen="F_0-17",
            total_female_age_group_eighteen_to_fiftynine="F_18-59",
            total_female_age_group_sixty_plus="F_60+",
            total_other_age_group_female="F_other age group",
            total_male_age_group_less_than_five='M_<5',
            total_male_age_group_five_to_forteen='M_5-14',
            total_male_age_group_fifteen_to_twenty_four="M_15-24",
            total_male_age_group_zero_to_seventeen="M_0-17",
            total_male_age_group_eighteen_to_fiftynine="M_18-59",
            total_male_age_group_sixty_plus="M_60+",
            total_other_age_group_male="M_other age group",
        )
        entries = EntryExtractionFilterSet(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            countries=ArrayAgg('figures__country__name', distinct=True),
            countries_iso3=StringAgg('figures__country__iso3', delimiter='; ', distinct=True),
            categories=ArrayAgg('figures__category', distinct=True),
            terms=ArrayAgg('figures__term', distinct=True),
            min_fig_start=Min('figures__start_date'),
            min_fig_end=Min('figures__end_date'),
            max_fig_start=Max('figures__start_date'),
            max_fig_end=Max('figures__end_date'),
            centroid_lat=Avg('figures__geo_locations__lat'),
            centroid_lon=Avg('figures__geo_locations__lon'),
            sources_name=StringAgg('sources__name', delimiter='; '),
            source_types=StringAgg('sources__organization_kind__name', delimiter='; '),
            publishers_name=StringAgg('publishers__name', delimiter='; '),
            publisher_types=StringAgg('publishers__organization_kind__name', delimiter='; '),
            figures_count=models.Count('figures', distinct=True),
            **cls._total_figure_disaggregation_subquery(),
        ).annotate(
            centroid=models.Case(
                models.When(
                    centroid_lat__isnull=False,
                    then=Concat(
                        F('centroid_lat'), Value(', '), F('centroid_lon'),
                        output_field=models.CharField()
                    )
                ),
                default=Value('')
            )
        ).annotate(
            total_female_age_group_less_than_five=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[LESS_THAN_FIVE]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_female_age_group_five_to_forteen=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[FIVE_TO_FOURTEEN]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_female_age_group_fifteen_to_twenty_four=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[
                            FIFTEEN_TO_TWENTRY_FOUR
                        ]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_female_age_group_zero_to_seventeen=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[ZERO_TO_SEVENTEEN]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_female_age_group_eighteen_to_fiftynine=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[EIGHTEEN_TO_FIFTYNINE]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_female_age_group_sixty_plus=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[SIXTY_PLUS]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_other_age_group_female=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.FEMALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[OTHER_AGES]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_less_than_five=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[LESS_THAN_FIVE]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_five_to_forteen=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[FIVE_TO_FOURTEEN]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_fifteen_to_twenty_four=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[
                            FIFTEEN_TO_TWENTRY_FOUR
                        ]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_zero_to_seventeen=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[ZERO_TO_SEVENTEEN]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_eighteen_to_fiftynine=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[EIGHTEEN_TO_FIFTYNINE]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_male_age_group_sixty_plus=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[SIXTY_PLUS]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            ),
            total_other_age_group_male=Sum(
                Case(When(
                    Q(
                        figures__disaggregation_age__sex=GENDER_TYPE.MALE
                    ) & Q(
                        figures__disaggregation_age__category__age_group__in=AGE_CATEGORIES_TO_EXPORT[OTHER_AGES]
                    ), then='figures__disaggregation_age__value'), output_field=models.IntegerField(), default=0)
            )
        ).order_by('-created_at').select_related(
            'created_by',
        ).prefetch_related(
            'figures',
            'sources',
            'publishers',
            'figures__disaggregation_age',
            'figures__disaggregation_age__category',
        ).order_by('-id')

        def transformer(datum):
            return {
                **datum,
                'categories': '; '.join([category.name if category else "" for category in datum['categories']]),
                'terms': '; '.join([term.name if term else "" for term in datum['terms']]),
            }

        return {
            'headers': headers,
            'data': entries.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': transformer,
        }
    # Properties

    # FIXME: will deprecate
    @property
    def is_under_review(self):
        return self.review_status == EntryReviewer.REVIEW_STATUS.UNDER_REVIEW

    # FIXME: will deprecate
    @property
    def is_reviewed(self):
        return self.review_status == EntryReviewer.REVIEW_STATUS.REVIEW_COMPLETED

    # FIXME: will deprecate
    @property
    def is_signed_off(self):
        return self.review_status == EntryReviewer.REVIEW_STATUS.SIGNED_OFF

    @property
    def latest_reviews(self):
        return self.reviews.order_by(
            *Review.UNIQUE_TOGETHER_WITHOUT_ENTRY_FIELDS, '-created_at'
        ).distinct(
            *Review.UNIQUE_TOGETHER_WITHOUT_ENTRY_FIELDS
        )

    @property
    def source_methodology(self) -> str:
        return '\n\n'.join(self.sources.
                           filter(methodology__isnull=False).
                           exclude(methodology='').
                           values_list('methodology', flat=True))

    @staticmethod
    def clean_url_and_document(values: dict, instance=None) -> OrderedDict:
        errors = OrderedDict()
        if instance:
            # we wont allow updates to entry sources
            return errors
        url = values.get('url', getattr(instance, 'url', None))
        document = values.get('document', getattr(instance, 'document', None))
        if not url and not document:
            errors['url'] = gettext('Please fill the URL or upload a document.')
            errors['document'] = gettext('Please fill the URL or upload a document.')
        return errors
    # Methods

    def can_be_updated_by(self, user: User) -> bool:
        """
        used to check before deleting as well
            i.e `can be DELETED by`
        """
        return not self.is_signed_off

    def update_associated_parked_item(self):
        self.associated_parked_item.status = ParkedItem.PARKING_LOT_STATUS.REVIEWED
        self.associated_parked_item.save()

    # Core

    def save(self, *args, **kwargs):
        if self.associated_parked_item:
            self.update_associated_parked_item()
        return super().save(*args, **kwargs)

    class Meta:
        permissions = (('sign_off_entry', 'Can sign off the entry'),)

    # Dunders

    def __str__(self):
        return f'Entry {self.article_title}'
