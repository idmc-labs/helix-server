from collections import OrderedDict
from datetime import date
import logging
from typing import Optional, Union, Dict, Callable, List
from uuid import uuid4
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates.general import StringAgg, ArrayAgg
from django.db.models import JSONField
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.query import QuerySet
from django.db.models import (
    F, Value, Min, Max, Q, ExpressionWrapper,
    fields, Case, When,
)
from django.db.models.functions import Concat, ExtractYear, Cast
from django.utils.translation import gettext_lazy as _, gettext
from django.utils.crypto import get_random_string
from django.db.models.expressions import RawSQL
from django.utils import timezone
from django_enumfield import enum
from helix.settings import FIGURE_NUMBER
from helix.storages import get_external_storage
from apps.contrib.models import (
    MetaInformationAbstractModel,
    UUIDAbstractModel,
    MetaInformationArchiveAbstractModel,
)
from utils.common import get_string_from_list
from utils.db import Array
from utils.fields import CachedFileField, generate_full_media_url
from apps.contrib.commons import DATE_ACCURACY
from apps.review.models import Review
from apps.parking_lot.models import ParkedItem
from apps.common.enums import GENDER_TYPE
from apps.notification.models import Notification
from apps.common.utils import (
    format_event_codes,
    format_locations,
    EXTERNAL_ARRAY_SEPARATOR,
    EXTERNAL_TUPLE_SEPARATOR,
)
from .documents import README_DATA

logger = logging.getLogger(__name__)
User = get_user_model()
CANNOT_UPDATE_MESSAGE = _('You cannot sign off the entry.')


class OSMName(UUIDAbstractModel, models.Model):
    class OSM_ACCURACY(enum.Enum):
        ADM0 = 0
        ADM1 = 1
        ADM2 = 2
        ADM3 = 3
        POINT = 4

        __labels__ = {
            ADM0: _('Country/territory (AM0)'),
            ADM1: _('State/Region/Province (ADM1)'),
            ADM2: _('District/Zone/Department (ADM2)'),
            ADM3: _('County/City/town/Village/Woreda (ADM3)'),
            POINT: _('Point'),
        }

    class IDENTIFIER(enum.Enum):
        ORIGIN = 0
        DESTINATION = 1
        ORIGIN_AND_DESTINATION = 2

        __labels__ = {
            ORIGIN: _('Origin'),
            DESTINATION: _('Destination'),
            ORIGIN_AND_DESTINATION: _('Origin and destination'),
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
    age_from = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Age From'))
    age_to = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Age To'))

    def __str__(self):
        return str(self.pk)


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

    class SOURCES_RELIABILITY(enum.Enum):
        LOW = 0
        MEDIUM = 1
        HIGH = 2
        LOW_TO_HIGH = 3
        LOW_TO_MEDIUM = 4
        MEDIUM_TO_HIGH = 5

        __labels__ = {
            LOW: _('Low'),
            MEDIUM: _('Medium'),
            HIGH: _('High'),
            LOW_TO_HIGH: _('Low to high'),
            LOW_TO_MEDIUM: _('Low to medium'),
            MEDIUM_TO_HIGH: _('Medium to high'),
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
        PEOPLE_DISPLACED_ACROSS_BORDERS_FLOW = 22

        __labels__ = {
            IDPS: _('IDPs'),
            RETURNEES: _('Returnees'),
            RETURN: _('Return'),
            LOCALLY_INTEGRATED_IDPS: _('Locally Integrated IDPs'),
            IDPS_SETTLED_ELSEWHERE: _('IDPs Settled Elsewhere'),
            PEOPLE_DISPLACED_ACROSS_BORDERS: _('People displaced across borders'),
            NEW_DISPLACEMENT: _('Internal Displacements'),
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
            FAILED_RELOCATION_ELSEWHERE: _('Failed relocation elsewhere'),
            PEOPLE_DISPLACED_ACROSS_BORDERS_FLOW: _('People displaced across borders'),
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

    class FIGURE_REVIEW_STATUS(enum.Enum):
        REVIEW_NOT_STARTED = 0
        REVIEW_IN_PROGRESS = 1
        APPROVED = 2
        REVIEW_RE_REQUESTED = 3

        __labels__ = {
            REVIEW_NOT_STARTED: _("Review not started"),
            REVIEW_IN_PROGRESS: _("Review in progress"),
            APPROVED: _("Approved"),
            REVIEW_RE_REQUESTED: _("Review re-requested"),
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
        'event.DisasterCategory', verbose_name=_('Figure Hazard Category'),
        blank=True, null=True,
        related_name='figures', on_delete=models.SET_NULL
    )
    disaster_sub_category = models.ForeignKey(
        'event.DisasterSubCategory', verbose_name=_('Figure Hazard Sub Category'),
        blank=True, null=True,
        related_name='figures', on_delete=models.SET_NULL
    )
    disaster_type = models.ForeignKey(
        'event.DisasterType', verbose_name=_('Figure Hazard Type'),
        blank=True, null=True,
        related_name='figures', on_delete=models.SET_NULL
    )
    disaster_sub_type = models.ForeignKey(
        'event.DisasterSubType', verbose_name=_('Figure Hazard Sub Type'),
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
    sources = models.ManyToManyField(
        'organization.Organization', verbose_name=_('Source'),
        blank=True, related_name='sourced_figures'
    )
    approved_by = models.ForeignKey(
        'users.User', verbose_name=_('Approved by'), null=True, blank=True,
        related_name='figure_approved_by', on_delete=models.SET_NULL
    )
    approved_on = models.DateTimeField(verbose_name='Assigned at', null=True, blank=True)
    review_status = enum.EnumField(
        enum=FIGURE_REVIEW_STATUS, verbose_name=_('Figure status'),
        default=FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED
    )

    # Types
    event_id: int

    class Meta:
        indexes = [
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
            models.Index(fields=['country']),
            models.Index(fields=['category']),
            models.Index(fields=['role']),
            models.Index(fields=['event']),
        ]
        permissions = (
            ('approve_figure', 'Can approve/unapprove figure'),
        )

    # NOTE: Any change done here on the list should also be done on the client
    SUPPORTED_OSMNAME_COUNTRY_CODES = {
        'AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AO', 'AQ', 'AR', 'AS', 'AT',
        'AU', 'AZ', 'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BJ', 'BM',
        'BN', 'BO', 'BQ', 'BR', 'BS', 'BT', 'BW', 'BY', 'BZ', 'CA', 'CD', 'CF',
        'CG', 'CH', 'CI', 'CK', 'CL', 'CM', 'CN', 'CO', 'CR', 'CU', 'CV', 'CY',
        'CZ', 'DE', 'DJ', 'DK', 'DM', 'DO', 'DZ', 'EC', 'EE', 'EG', 'EH', 'ER',
        'ES', 'ET', 'FI', 'FJ', 'FK', 'FM', 'FO', 'FR', 'GA', 'GB', 'GD', 'GE',
        'GG', 'GH', 'GI', 'GL', 'GM', 'GN', 'GQ', 'GR', 'GS', 'GT', 'GW', 'GY',
        'HN', 'HR', 'HT', 'HU', 'ID', 'IE', 'IL', 'IM', 'IN', 'IO', 'IQ', 'IR',
        'IS', 'IT', 'JE', 'JM', 'JO', 'JP', 'KE', 'KG', 'KH', 'KI', 'KM', 'KN',
        'KP', 'KR', 'KW', 'KY', 'KZ', 'LA', 'LB', 'LC', 'LI', 'LK', 'LR', 'LS',
        'LT', 'LU', 'LV', 'LY', 'MA', 'MC', 'MD', 'ME', 'MG', 'MH', 'MK', 'ML',
        'MM', 'MN', 'MP', 'MR', 'MS', 'MT', 'MU', 'MV', 'MW', 'MX', 'MY', 'MZ',
        'NA', 'NE', 'NG', 'NI', 'NL', 'NO', 'NP', 'NR', 'NU', 'NZ', 'OM', 'PA',
        'PE', 'PG', 'PH', 'PK', 'PL', 'PN', 'PS', 'PT', 'PW', 'PY', 'QA',
        'RO', 'RS', 'RU', 'RW', 'SA', 'SB', 'SC', 'SD', 'SE', 'SG', 'SH', 'SI',
        'SK', 'SL', 'SM', 'SN', 'SO', 'SR', 'SS', 'ST', 'SV', 'SY', 'SZ', 'TA',
        'TC', 'TD', 'TF', 'TG', 'TH', 'TJ', 'TK', 'TL', 'TM', 'TN', 'TO', 'TR',
        'TT', 'TV', 'TW', 'TZ', 'UA', 'UG', 'UM', 'US', 'UY', 'UZ', 'VA', 'VC',
        'VE', 'VG', 'VN', 'VU', 'WF', 'WS', 'XK', 'YE', 'ZA', 'ZM', 'ZW',
    }

    # methods
    @classmethod
    def _filtered_nd_figures(
        cls,
        categories: List[int],
        qs: QuerySet,
        start_date: Optional[date],
        end_date: Optional[date],
    ):
        # NOTE: We should write this query without using union
        year_difference = ExpressionWrapper(
            ExtractYear('end_date') - ExtractYear('start_date'),
            output_field=fields.IntegerField(),
        )
        qs = qs.annotate(year_difference=year_difference)

        same_year_figures_filter = dict(
            year_difference__lt=1,
        )
        multiple_year_figures = dict(
            year_difference__gte=1,
        )

        if len(categories) > 1:
            same_year_figures_filter.update(category__in=categories)
            multiple_year_figures.update(category__in=categories)
        else:
            same_year_figures_filter.update(
                category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
            )
            multiple_year_figures.update(
                category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
            )

        if start_date:
            same_year_figures_filter = dict(
                **same_year_figures_filter,
                start_date__gte=start_date,
            )
            multiple_year_figures = dict(
                **multiple_year_figures,
                end_date__gte=start_date
            )

        if end_date:
            same_year_figures_filter = dict(
                **same_year_figures_filter,
                start_date__lte=end_date
            )
            multiple_year_figures = dict(
                **multiple_year_figures,
                end_date__lte=end_date,
            )

        return qs.filter(
            models.Q(**same_year_figures_filter) |
            models.Q(**multiple_year_figures)
        )

    @classmethod
    def filtered_nd_figures(
        cls,
        qs: QuerySet,
        start_date: Optional[date],
        end_date: Optional[date] = None,
    ):
        return cls._filtered_nd_figures(
            [Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value],
            qs,
            start_date,
            end_date=end_date,
        )

    @classmethod
    def filtered_nd_figures_for_listing(
        cls,
        qs: QuerySet,
        start_date: Optional[date],
        end_date: Optional[date] = None,
    ):
        return cls._filtered_nd_figures(
            cls.flow_list(),
            qs,
            start_date,
            end_date=end_date,
        )

    @classmethod
    def annotate_stock_and_flow_dates(cls):
        return {
            'flow_start_date': Case(
                When(category__in=Figure.flow_list(), then=F('start_date'))
            ),
            'flow_end_date': Case(
                When(category__in=Figure.flow_list(), then=F('end_date'))
            ),
            'flow_start_date_accuracy': Case(
                When(category__in=Figure.flow_list(), then=F('start_date_accuracy'))
            ),
            'flow_end_date_accuracy': Case(
                When(category__in=Figure.flow_list(), then=F('end_date_accuracy'))
            ),
            'stock_date': Case(
                When(category__in=Figure.stock_list(), then=F('start_date'))
            ),
            'stock_reporting_date': Case(
                When(category__in=Figure.stock_list(), then=F('end_date'))
            ),
            'stock_date_accuracy': Case(
                When(category__in=Figure.stock_list(), then=F('start_date_accuracy'))
            ),
        }

    @classmethod
    def annotate_sources_reliability(cls):
        from apps.organization.models import OrganizationKind
        return {
            'lowest_source_reliability': models.Min(
                'sources__organization_kind__reliability', output_field=models.IntegerField()
            ),
            'highest_source_reliability': models.Max(
                'sources__organization_kind__reliability', output_field=models.IntegerField()
            ),
            'sources_reliability': Case(
                When(
                    lowest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.LOW.value,
                    highest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.LOW.value,
                    then=Value(Figure.SOURCES_RELIABILITY.LOW)
                ),
                When(
                    lowest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.MEDIUM.value,
                    highest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.MEDIUM.value,
                    then=Value(Figure.SOURCES_RELIABILITY.MEDIUM)
                ),
                When(
                    lowest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.HIGH.value,
                    highest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.HIGH.value,
                    then=Value(Figure.SOURCES_RELIABILITY.HIGH)
                ),
                When(
                    lowest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.LOW.value,
                    highest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.HIGH.value,
                    then=Value(Figure.SOURCES_RELIABILITY.LOW_TO_HIGH)
                ),
                When(
                    lowest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.MEDIUM.value,
                    highest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.HIGH.value,
                    then=Value(Figure.SOURCES_RELIABILITY.MEDIUM_TO_HIGH)
                ),
                When(
                    lowest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.LOW.value,
                    highest_source_reliability=OrganizationKind.ORGANIZATION_RELIABILITY.MEDIUM.value,
                    then=Value(Figure.SOURCES_RELIABILITY.LOW_TO_MEDIUM)
                ),
                output_field=models.CharField(),
            )
        }

    @classmethod
    def stock_list(cls):
        return [
            Figure.FIGURE_CATEGORY_TYPES.IDPS.value,
            Figure.FIGURE_CATEGORY_TYPES.RETURNEES.value,
            Figure.FIGURE_CATEGORY_TYPES.LOCALLY_INTEGRATED_IDPS.value,
            Figure.FIGURE_CATEGORY_TYPES.IDPS_SETTLED_ELSEWHERE.value,
            Figure.FIGURE_CATEGORY_TYPES.PEOPLE_DISPLACED_ACROSS_BORDERS.value,
            Figure.FIGURE_CATEGORY_TYPES.PARTIAL_STOCK.value,
            Figure.FIGURE_CATEGORY_TYPES.UNVERIFIED_STOCK.value,
        ]

    @classmethod
    def flow_list(cls) -> List[int]:
        return [
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
            Figure.FIGURE_CATEGORY_TYPES.RETURN.value,
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
            Figure.FIGURE_CATEGORY_TYPES.FAILED_RELOCATION_ELSEWHERE.value,
            Figure.FIGURE_CATEGORY_TYPES.BIRTH.value,
            Figure.FIGURE_CATEGORY_TYPES.UNVERIFIED_FLOW.value,
            Figure.FIGURE_CATEGORY_TYPES.PEOPLE_DISPLACED_ACROSS_BORDERS_FLOW.value,
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
        start_date: Optional[date],
        end_date: Optional[Union[date, models.OuterRef]] = None,
    ):
        qs = qs.filter(
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS.value,
        )
        if start_date:
            qs = qs.filter(end_date__gte=start_date)
        if end_date:
            qs = qs.filter(end_date=end_date)
        return qs

    @classmethod
    def filtered_idp_figures_for_listing(
        cls,
        qs: QuerySet,
        start_date: Optional[date],
        end_date: Optional[date] = None,
    ):
        qs = qs.filter(
            category__in=cls.stock_list()
        )
        if start_date:
            qs = qs.filter(end_date__gte=start_date)
        if end_date:
            qs = qs.filter(end_date__lte=end_date)
        return qs

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.extraction.filters import ReportFigureExtractionFilterSet

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        qs = ReportFigureExtractionFilterSet(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs
        return cls.get_figure_excel_sheets_data(qs)

    @classmethod
    def get_figure_excel_sheets_data(cls, figures: models.QuerySet):

        from apps.crisis.models import Crisis

        headers = OrderedDict(
            id='ID',
            old_id='Old ID',
            created_at='Created at',
            modified_at='Updated at',
            country__iso3='ISO3',
            country__idmc_short_name='Country',
            centroid='Centroid',
            centroid_lat='Lat',  # Newly added but related to centroid
            centroid_lon='Lon',  # Newly added but related to centroid
            country__region__name='Region',
            country__geographical_group__name='Geographical region',
            figure_cause='Figure cause',
            year='Year',
            category='Figure category',
            role='Figure role',
            total_figures='Total figures',
            reported='Reported',
            term='Figure term',
            unit='Unit',
            quantifier='Quantifier',
            household_size='Household size',
            is_housing_destruction='Is housing destruction',
            displacement_occurred='Displacement occurred',
            include_idu='Include in IDU',
            excerpt_idu='Excerpt IDU',
            violence__name='Violence type',
            violence_sub_type__name='Violence sub type',
            osv_sub_type__name='OSV sub type',
            context_of_violences='Context of violences',
            disaster_category__name='Hazard category',
            disaster_sub_category__name='Hazard sub category',
            disaster_type__name='Hazard type',
            disaster_sub_type__name='Hazard sub type',
            event__other_sub_type__name='Other event sub type',
            flow_start_date='Start date',
            flow_start_date_accuracy='Start date accuracy',
            flow_end_date='End date',
            flow_end_date_accuracy='End date accuracy',
            stock_date='Stock date',
            stock_date_accuracy='Stock date accuracy',
            stock_reporting_date='Stock reporting date',
            calculation_logic='Analysis and calculation logic',
            figure_link='Link',
            publishers_name='Publishers',
            sources_name='Sources',
            sources_type='Sources type',
            sources_reliability='Sources reliability',
            sources_methodology='Sources methodology',
            source_excerpt='Source excerpt',
            entry_url_or_document_url='Source url',
            entry__preview__pdf='Source url snapshot',
            source_document='Source document',
            entry__id='Entry ID',
            entry__old_id='Entry old ID',
            entry__article_title='Entry title',
            entry_link='Entry link',
            disaggregation_disability='Disability',
            disaggregation_indigenous_people='Indigenous people',
            event__id='Event ID',
            event__old_id='Event old ID',
            event__name='Event name',
            event__event_type='Event cause',
            event_main_trigger='Event main trigger',
            event__start_date='Event start date',
            event__end_date='Event end date',
            event__start_date_accuracy='Event start date accuracy',
            event__end_date_accuracy='Event end date accuracy',
            event__event_narrative='Event narrative',
            event__crisis_id='Crisis ID',
            event__crisis__name='Crisis name',
            tags_name='Tags',
            is_disaggregated='Has disaggregated data',
            review_status='Revision progress',
            event__assignee__full_name='Assignee',
            created_by__full_name='Created by',
            last_modified_by__full_name='Updated by',
            event_codes='Event codes (Code:Type)',
            locations__display_name='Location Name',
            locations_lat_lon='Locations',
            locations__accuracy='Location accuracy',
            locations__identifier='Type of Point',
            locations='Locations (Name:Lat, Lon:Accuracy:Type)',
        )
        values = figures.annotate(
            **Figure.annotate_stock_and_flow_dates(),
            **Figure.annotate_sources_reliability(),
            centroid_lat=RawSQL('country_country.centroid[2]', params=()),
            centroid_lon=RawSQL('country_country.centroid[1]', params=()),
            entry_url_or_document_url=models.Case(
                models.When(
                    entry__document__isnull=False,
                    then=F('entry__document_url')
                ),
                models.When(
                    entry__document__isnull=True,
                    then=F('entry__url')
                ),
                output_field=models.CharField()
            ),
            source_document=models.Case(
                models.When(
                    entry__document__isnull=False,
                    then=F('entry__document__attachment')
                ),
                output_field=models.CharField()
            ),
            entry_link=Concat(
                Value(settings.FRONTEND_BASE_URL),
                Value('/entries/'),
                F('entry__id'),
                output_field=models.CharField()
            ),
            figure_link=Concat(
                Value(settings.FRONTEND_BASE_URL),
                Value('/entries/'),
                F('entry__id'),
                Value('/?id='),
                F('id'),
                Value('#/figures-and-analysis'),
                output_field=models.CharField()
            ),
            publishers_name=StringAgg(
                'entry__publishers__name',
                EXTERNAL_ARRAY_SEPARATOR,
                filter=~Q(entry__publishers__name=''),
                distinct=True, output_field=models.CharField()
            ),
            year=ExtractYear("end_date"),
            context_of_violences=StringAgg(
                'context_of_violence__name', EXTERNAL_ARRAY_SEPARATOR,
                distinct=True, output_field=models.CharField()
            ),
            tags_name=StringAgg(
                'tags__name', EXTERNAL_ARRAY_SEPARATOR,
                distinct=True, output_field=models.CharField()
            ),
            sources_name=StringAgg(
                'sources__name', EXTERNAL_ARRAY_SEPARATOR,
                distinct=True, output_field=models.CharField()
            ),
            sources_type=StringAgg(
                'sources__organization_kind__name', EXTERNAL_ARRAY_SEPARATOR,
                distinct=True, output_field=models.CharField()
            ),
            sources_methodology=StringAgg(
                'sources__methodology', EXTERNAL_ARRAY_SEPARATOR,
                distinct=True, output_field=models.CharField()
            ),
            centroid=Concat(
                F('centroid_lat'),
                Value(EXTERNAL_TUPLE_SEPARATOR),
                F('centroid_lon'),
                output_field=models.CharField()
            ),
            event_main_trigger=Case(
                When(
                    event__event_type=Crisis.CRISIS_TYPE.CONFLICT,
                    then=F('event__violence_sub_type__name')
                ),
                When(
                    event__event_type=Crisis.CRISIS_TYPE.DISASTER,
                    then=F('event__disaster_sub_type__name')
                ),
                When(
                    event__event_type=Crisis.CRISIS_TYPE.OTHER,
                    then=F('event__other_sub_type__name')
                ),
                output_field=models.CharField()
            ),
            event_codes=ArrayAgg(
                Array(
                    F('event__event_code__event_code'),
                    Cast(F('event__event_code__event_code_type'), models.CharField()),
                    output_field=ArrayField(models.CharField()),
                ),
                distinct=True,
                filter=models.Q(event__event_code__country__id=F('country__id')),
            ),
            locations=ArrayAgg(
                Array(
                    F('geo_locations__display_name'),
                    Concat(
                        F('geo_locations__lat'),
                        Value(EXTERNAL_TUPLE_SEPARATOR),
                        F('geo_locations__lon'),
                        output_field=models.CharField(),
                    ),
                    Cast('geo_locations__accuracy', models.CharField()),
                    Cast('geo_locations__identifier', models.CharField()),
                    output_field=ArrayField(models.CharField()),
                ),
                distinct=True,
                filter=~Q(
                    Q(geo_locations__display_name__isnull=True) | Q(geo_locations__display_name='')
                ),
            ),
            locations__display_name=StringAgg(
                'geo_locations__display_name',
                EXTERNAL_ARRAY_SEPARATOR,
                output_field=models.CharField()
            ),
            locations__accuracy=ArrayAgg(
                Cast('geo_locations__accuracy', models.IntegerField()),
                filter=Q(geo_locations__accuracy__isnull=False)
            ),
            locations__identifier=ArrayAgg(
                Cast('geo_locations__identifier', models.IntegerField()),
                filter=Q(geo_locations__accuracy__isnull=False)
            ),
            locations_lat_lon=StringAgg(
                Concat(
                    F('geo_locations__lat'),
                    Value(EXTERNAL_TUPLE_SEPARATOR),
                    F('geo_locations__lon'),
                    output_field=models.CharField(),
                    distinct=True
                ),
                EXTERNAL_ARRAY_SEPARATOR,
                filter=models.Q(geo_locations__isnull=False),
                output_field=models.CharField(),
            ),
        ).order_by(
            'created_at',
        ).values(*[header for header in headers.keys()])

        def transformer(datum):

            def get_enum_label(key, Enum):
                val = datum[key]
                obj = Enum.get(val)
                return getattr(obj, "label", val)

            return {
                **datum,
                'include_idu': 'Yes' if datum['include_idu'] else 'No',
                'entry__preview__pdf': generate_full_media_url(datum['entry__preview__pdf'], absolute=True),
                'is_housing_destruction': 'Yes' if datum['is_housing_destruction'] else 'No',
                'stock_date_accuracy': get_enum_label(
                    'stock_date_accuracy', DATE_ACCURACY
                ),
                'flow_start_date_accuracy': get_enum_label(
                    'flow_start_date_accuracy', DATE_ACCURACY
                ),
                'flow_end_date_accuracy': get_enum_label(
                    'flow_end_date_accuracy', DATE_ACCURACY
                ),
                'quantifier': get_enum_label(
                    'quantifier', Figure.QUANTIFIER
                ),
                'unit': get_enum_label('unit', Figure.UNIT),
                'role': get_enum_label('role', Figure.ROLE),
                'term': get_enum_label('term', Figure.FIGURE_TERMS),
                'category': get_enum_label(
                    'category', Figure.FIGURE_CATEGORY_TYPES
                ),
                'displacement_occurred': get_enum_label(
                    'displacement_occurred', Figure.DISPLACEMENT_OCCURRED
                ),
                'figure_cause': get_enum_label(
                    'figure_cause', Crisis.CRISIS_TYPE
                ),
                'sources_reliability': get_enum_label(
                    'sources_reliability', Figure.SOURCES_RELIABILITY
                ),
                'source_document': generate_full_media_url(datum['source_document'], absolute=True),
                'centroid': datum['centroid'],
                'event__event_type': get_enum_label(
                    'event__event_type', Crisis.CRISIS_TYPE
                ),
                'event__start_date_accuracy': get_enum_label(
                    'event__start_date_accuracy', DATE_ACCURACY
                ),
                'event__end_date_accuracy': get_enum_label(
                    'event__end_date_accuracy', DATE_ACCURACY
                ),
                'review_status': get_enum_label(
                    'review_status', Figure.FIGURE_REVIEW_STATUS
                ),
                'is_disaggregated': 'Yes' if datum['is_disaggregated'] else 'No',
                'event_codes': format_event_codes(datum['event_codes']),
                'locations': format_locations(datum['locations']),
                'locations__accuracy': get_string_from_list([
                    OSMName.OSM_ACCURACY(item).label for item in datum['locations__accuracy']
                ]),
                'locations__identifier': get_string_from_list([
                    OSMName.IDENTIFIER(item).label for item in datum['locations__identifier']
                ]),
            }

        readme_data = [
            {
                'title': 'Readme',
                'results': {
                    'headers': OrderedDict(
                        column_name='Column Name',
                        description='Description',
                    ),
                    'data': README_DATA,
                }
            }
        ]
        return {
            'headers': headers,
            'data': values,
            'formulae': None,
            'transformer': transformer,
            'readme_data': readme_data,
        }

    @classmethod
    def can_be_created_by(cls, user: User, entry: 'Entry') -> bool:
        return entry.can_be_updated_by(user)

    @classmethod
    def update_figure_status(cls, figure):
        review_comments_count = figure.figure_review_comments.count()

        # NOTE: State machine with states defined in FIGURE_REVIEW_STATUS
        if (
            review_comments_count > 0 and
            (figure.review_status == Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED or
                figure.review_status == Figure.FIGURE_REVIEW_STATUS.APPROVED)
        ):
            figure.review_status = Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS
            figure.save()
        elif (
            review_comments_count <= 0 and
            (figure.review_status == Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS or
                figure.review_status == Figure.FIGURE_REVIEW_STATUS.APPROVED)
        ):
            figure.review_status = Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED
            figure.save()

    # TODO: move this to event model
    @classmethod
    def update_event_status_and_send_notifications(cls, event_id):
        from apps.event.models import Event

        # FIXME: should we directly get event_id from the args instead?
        event_with_stats = Event.objects.filter(
            id=event_id
        ).annotate(
            **Event.annotate_review_figures_count()
        ).first()

        review_approved_count = event_with_stats.review_approved_count
        review_re_request_count = event_with_stats.review_re_request_count
        review_in_progress_count = event_with_stats.review_in_progress_count
        total_count = event_with_stats.total_count

        prev_status = event_with_stats.review_status

        if prev_status == Event.EVENT_REVIEW_STATUS.REVIEW_NOT_STARTED:
            if review_approved_count == total_count and review_approved_count > 0:
                event_with_stats.review_status = Event.EVENT_REVIEW_STATUS.APPROVED.value
            elif review_in_progress_count > 0 or review_approved_count > 0 or review_re_request_count > 0:
                event_with_stats.review_status = Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS.value
        elif prev_status == Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS:
            if review_approved_count == total_count and review_approved_count > 0:
                event_with_stats.review_status = Event.EVENT_REVIEW_STATUS.APPROVED.value
        elif prev_status == Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED:
            if review_approved_count == total_count and review_approved_count > 0:
                event_with_stats.review_status = Event.EVENT_REVIEW_STATUS.APPROVED.value
        elif prev_status == Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED:
            if review_approved_count == total_count and review_approved_count > 0:
                event_with_stats.review_status = Event.EVENT_REVIEW_STATUS.APPROVED.value
        elif prev_status == Event.EVENT_REVIEW_STATUS.APPROVED:
            if review_approved_count != total_count:
                event_with_stats.review_status = Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED
        elif prev_status == Event.EVENT_REVIEW_STATUS.SIGNED_OFF:
            if review_approved_count != total_count:
                event_with_stats.review_status = Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED
        event_with_stats.save()

        # TODO: add notification for transition to APPROVED_BUT_CHANGED, SIGNED_OFF_BUT_CHANGED, REVIEW_IN_PROGRESS?
        if (
            prev_status != event_with_stats.review_status and
            event_with_stats.review_status == Event.EVENT_REVIEW_STATUS.APPROVED
        ):
            recipients = [user['id'] for user in Event.regional_coordinators(event_with_stats)]
            if (event_with_stats.created_by_id):
                recipients.append(event_with_stats.created_by_id)
            if (event_with_stats.assignee_id):
                recipients.append(event_with_stats.assignee_id)

            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                type=Notification.Type.EVENT_APPROVED,
                event=event_with_stats,
                actor=None,
            )

    def can_be_updated_by(self, user: User) -> bool:
        """
        used to check before deleting as well
        """
        return self.entry.can_be_updated_by(user)


class FigureTag(MetaInformationAbstractModel):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.entry.filters import FigureTagFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id='ID',
            name='Name',
            created_at='Created At',
            modified_at='Modified At',
            created_by__full_name='Created By',
            last_modified_by__full_name='Last Modified By',
        )
        data = FigureTagFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.order_by('created_at')

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': None,
        }


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
                    start_date=None,
                    end_date=timezone.now().date(),
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
            id='ID',
            created_by__full_name='Created by',
            created_at='Created at',
            last_modified_by__full_name='Updated by',
            modified_at='Updated at',
            is_confidential='Confidential',
            publish_date='Publish date',
            figure_causes='Figure causes',
            countries='Countries affected',
            article_title='Entry title',
            url='URL',
            preview__pdf='URL snapshot',
            document__attachment='Document',
            document__mimetype='Filetype',
            document__filetype_detail='Filetype detail',
            sources_name='Sources',
            source_types='Source types',
            # Extra added fields
            old_id='Old ID',
            publishers_name='Publishers',
            publisher_types='Publisher types',
            idmc_analysis='Trends and patterns of displacement to be highlighted',
            countries_iso3='ISO3s affected',
            categories='Figure categories',
            terms='Figure terms',
            figures_count='Figures count',
            # **{
            #     cls.IDP_FIGURES_ANNOTATE: 'IDPs figure',
            #     cls.ND_FIGURES_ANNOTATE: 'ND figure',
            # },
            min_fig_start='Earliest figure start',
            max_fig_start='Latest figure start',
            min_fig_end='Earliest figure end',
            max_fig_end='Latest figure end',
            context_of_violences='Context of violences',
        )
        entries = EntryExtractionFilterSet(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            countries=StringAgg('figures__country__idmc_short_name', EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            countries_iso3=StringAgg('figures__country__iso3', EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            figure_causes=ArrayAgg('figures__figure_cause', distinct=True),
            categories=ArrayAgg('figures__category', distinct=True),
            terms=ArrayAgg('figures__term', distinct=True),
            min_fig_start=Min('figures__start_date'),
            min_fig_end=Min('figures__end_date'),
            max_fig_start=Max('figures__start_date'),
            max_fig_end=Max('figures__end_date'),
            sources_name=StringAgg('figures__sources__name', EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            source_types=StringAgg('figures__sources__organization_kind__name', EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            publishers_name=StringAgg('publishers__name', EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            publisher_types=StringAgg('publishers__organization_kind__name', EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            figures_count=models.Count('figures', distinct=True),
            context_of_violences=StringAgg('figures__context_of_violence__name', EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            # **cls._total_figure_disaggregation_subquery(),
        ).order_by('created_at')

        def transformer(datum):
            return {
                **datum,
                'preview__pdf': generate_full_media_url(datum['preview__pdf'], absolute=True),
                'document__attachment': generate_full_media_url(datum['document__attachment'], absolute=True),
                'is_confidential': 'Yes' if datum['is_confidential'] else 'No',
                'categories': get_string_from_list(
                    [category.label if category else "" for category in datum['categories']]
                ),
                'terms': get_string_from_list(
                    [term.label if term else "" for term in datum['terms']]
                ),
                'figure_causes': get_string_from_list(
                    [cause.label if cause else "" for cause in datum['categories']]
                ),
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

    # Dunders

    def __str__(self):
        return f'Entry {self.article_title}'


def dump_file_upload_to(instance, filename):
    date_str = timezone.now().strftime('%Y-%m-%d-%H-%M-%S')
    api_type = instance.api_type
    random_chars = get_random_string(length=5)
    return f'api-dump/{api_type}/{date_str}/{random_chars}/{filename}'


# FIXME: move this somewhere else
IDMC_WEBSITE_CLIENT_CODE = 'IDMCWSHSOLO009'


class ExternalApiDump(models.Model):

    class ExternalApiType(models.TextChoices):
        # There might be other external endpoints
        IDUS = 'idus', _('/external-api/idus/last-180-days/')
        IDUS_ALL = 'idus-all', _('/external-api/idus/all/')
        IDUS_ALL_DISASTER = 'idus-all-disaster', _('/external-api/idus/all/disaster/')

        GIDD_COUNTRY_REST = 'gidd-country-rest', _('/external-api/gidd/countries/')
        GIDD_CONFLICT_REST = 'gidd-conflict-rest', _('/external-api/gidd/conflicts/')
        GIDD_DISASTER_REST = 'gidd-disaster-rest', _('/external-api/gidd/disasters/')
        GIDD_DISPLACEMENT_REST = 'gidd-displacement-rest', _('/external-api/gidd/displacements/')
        GIDD_DISASTER_EXPORT_REST = 'gidd-disaster-export-rest', _('/external-api/gidd/disasters/export/')
        GIDD_DISPLACEMENT_EXPORT_REST = 'gidd-displacement-export-rest', _('/external-api/gidd/displacements/export/')
        GIDD_PUBLIC_FIGURE_ANALYSIS_REST = 'gidd-public-figure-analysis-rest', _(
            '/external-api/gidd/public-figure-analyses/'
        )

        GIDD_CONFLICT_GRAPHQL = 'gidd-conflict-graphql', _('query.giddPublicConflicts')
        GIDD_DISASTER_GRAPHQL = 'gidd-disaster-graphql', _('query.giddPublicDisasters')
        GIDD_DISPLACEMENT_DATA_GRAPHQL = 'gidd-displacement-data-graphql', _('query.giddPublicDisplacements')
        GIDD_PFA_GRAPHQL = 'gidd-public-figure-analysis-graphql', _('query.giddPublicFigureAnalysisList')
        GIDD_CONFLICT_STAT_GRAPHQL = 'gidd-conflict-stat-graphql', _('query.giddPublicConflictStatistics')
        GIDD_DISASTER_STAT_GRAPHQL = 'gidd-disaster-stat-graphql', _('query.giddPublicDisasterStatistics')
        GIDD_HAZARD_TYPES_GRAPHQL = 'gidd-hazard-type-graphql', _('query.giddPublicHazardTypes')
        GIDD_YEAR_GRAPHQL = 'gidd-year-graphql', _('query.giddPublicYear')
        GIDD_EVENT_GRAPHQL = 'gidd-event-graphql', _('query.giddPublicEvent')
        GIDD_COMBINED_STAT_GRAPHQL = 'gidd-combined-stat-graphql', _('query.giddPublicCombinedStatistics')
        GIDD_RELEASE_META_DATA_GRAPHQL = 'gidd-release-meta-data-graphql', _('query.giddPublicReleaseMetaData')
        GIDD_PUBLIC_COUNTRIES_GRAPHQL = 'gidd-public-countries-graphql', _('query.giddPublicCountries')

    class Status(models.IntegerChoices):
        PENDING = 0, 'Pending'
        COMPLETED = 1, 'Completed'
        FAILED = 2, 'Failed'

    @dataclass
    class Metadata:
        response_type: str  # Use Enum GraphQL - JSON/REST
        usage: Union[str, Callable]  # Use Enum: External/Public, HELIX, IDMC website, Dataset download
        description: str
        example_request: Union[str, Callable]

        def get_example_request(self, request, client_code: str):
            if callable(self.example_request):
                return self.example_request(request, client_code)
            return self.example_request

        def get_usage(self, request, client_code: str):
            if callable(self.usage):
                return self.usage(request, client_code)
            return self.usage

    API_TYPE_METADATA: Dict[ExternalApiType, Metadata] = {
        ExternalApiType.IDUS: Metadata(
            response_type='JSON',
            usage='External',
            description='IDUs from the last 180 days updated every 2 hours',
            example_request=(
                lambda request, client_code: request.build_absolute_uri(
                    ExternalApiDump.ExternalApiType.IDUS.label + f'?client_id={client_code}'
                )
            ),
        ),
        ExternalApiType.IDUS_ALL: Metadata(
            response_type='JSON',
            usage='External',
            description='All IDUs updated every 2 hours',
            example_request=(
                lambda request, client_code: request.build_absolute_uri(
                    ExternalApiDump.ExternalApiType.IDUS_ALL.label + f'?client_id={client_code}'
                )
            ),
        ),
        ExternalApiType.IDUS_ALL_DISASTER: Metadata(
            response_type='JSON',
            usage='External',
            description='IDUs for disaster updated every 2 hours',
            example_request=(
                lambda request, client_code: request.build_absolute_uri(
                    ExternalApiDump.ExternalApiType.IDUS_ALL_DISASTER.label + f'?client_id={client_code}'
                )
            ),
        ),

        ExternalApiType.GIDD_COUNTRY_REST: Metadata(
            response_type='REST - JSON',
            usage='External',
            description='List of countries with name, iso2 and iso3',
            example_request=(
                lambda request, client_code: request.build_absolute_uri(
                    ExternalApiDump.ExternalApiType.GIDD_COUNTRY_REST.label + f'?client_id={client_code}'
                )
            ),
        ),
        ExternalApiType.GIDD_CONFLICT_REST: Metadata(
            response_type='REST - JSON',
            usage='External',
            description='Conflict data aggregated by country and year',
            example_request=(
                lambda request, client_code: request.build_absolute_uri(
                    ExternalApiDump.ExternalApiType.GIDD_CONFLICT_REST.label + f'?client_id={client_code}'
                )
            ),
        ),
        ExternalApiType.GIDD_DISASTER_REST: Metadata(
            response_type='REST - JSON',
            usage='External',
            description='Disaster data aggregated by event, country and year',
            example_request=(
                lambda request, client_code: request.build_absolute_uri(
                    ExternalApiDump.ExternalApiType.GIDD_DISASTER_REST.label + f'?client_id={client_code}'
                )
            ),
        ),
        ExternalApiType.GIDD_DISPLACEMENT_REST: Metadata(
            response_type='REST - JSON',
            usage='External',
            description='Conflict and disaster data aggregated by country and year',
            example_request=(
                lambda request, client_code: request.build_absolute_uri(
                    ExternalApiDump.ExternalApiType.GIDD_DISASTER_REST.label + f'?client_id={client_code}'
                )
            ),
        ),
        ExternalApiType.GIDD_DISASTER_EXPORT_REST: Metadata(
            response_type='REST - XLSX',
            usage='External',
            description='Excel export of disaster data aggregated by event, country and year',
            example_request=(
                lambda request, client_code: request.build_absolute_uri(
                    ExternalApiDump.ExternalApiType.GIDD_DISASTER_EXPORT_REST.label + f'?client_id={client_code}'
                )
            ),
        ),
        ExternalApiType.GIDD_DISPLACEMENT_EXPORT_REST: Metadata(
            response_type='REST - XLSX',
            usage='External',
            description='Excel export of conflict and disaster data aggregated by country and year',
            example_request=(
                lambda request, client_code: request.build_absolute_uri(
                    ExternalApiDump.ExternalApiType.GIDD_DISPLACEMENT_EXPORT_REST.label + f'?client_id={client_code}'
                )
            ),
        ),
        ExternalApiType.GIDD_PUBLIC_FIGURE_ANALYSIS_REST: Metadata(
            response_type='REST - JSON',
            usage='External',
            description='Public figure analysis for a country,  year and cause',
            example_request=(
                lambda request, client_code: request.build_absolute_uri(
                    ExternalApiDump.ExternalApiType.GIDD_PUBLIC_FIGURE_ANALYSIS_REST.label + f'?client_id={client_code}'
                )
            ),
        ),

        ExternalApiType.GIDD_CONFLICT_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_DISASTER_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_DISPLACEMENT_DATA_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_PFA_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_CONFLICT_STAT_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_DISASTER_STAT_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_HAZARD_TYPES_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_YEAR_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_EVENT_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_COMBINED_STAT_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_RELEASE_META_DATA_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
        ExternalApiType.GIDD_PUBLIC_COUNTRIES_GRAPHQL: Metadata(
            response_type='GraphQL - JSON',
            usage=(
                lambda _, client_code: 'IDMC Website' if client_code == IDMC_WEBSITE_CLIENT_CODE else 'IDMC Widgets'
            ),
            description='',
            example_request='',
        ),
    }

    # Make sure metadata is provided for all types
    assert set(API_TYPE_METADATA.keys()) == set([i for i, _ in ExternalApiType.choices])

    dump_file = CachedFileField(
        verbose_name=_('Dump file'),
        blank=True, null=True,
        upload_to=dump_file_upload_to,
        storage=get_external_storage,
    )
    api_type = models.CharField(
        max_length=40,
        choices=ExternalApiType.choices,
    )
    status = models.IntegerField(
        choices=Status.choices, default=Status.PENDING
    )

    def __str__(self):
        return self.api_type
