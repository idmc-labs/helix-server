from collections import OrderedDict

from django.db import models
from django.contrib.postgres.aggregates.general import StringAgg
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
from django.contrib.postgres.fields import ArrayField
from django.forms import model_to_dict

from utils.common import get_string_from_list
from utils.common import add_clone_prefix

from apps.contrib.models import (
    MetaInformationAbstractModel,
    MetaInformationArchiveAbstractModel,
)
from apps.crisis.models import Crisis
from apps.contrib.commons import DATE_ACCURACY
from apps.entry.models import Figure
from apps.users.models import User, USER_ROLE


class NameAttributedModels(models.Model):
    name = models.CharField(_('Name'), max_length=256)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


# Models related to displacement caused by conflict


class Violence(NameAttributedModels):
    """
    Holds the possible violence choices
    """


class ViolenceSubType(NameAttributedModels):
    """
    Holds the possible violence sub types
    """
    violence = models.ForeignKey('Violence',
                                 related_name='sub_types', on_delete=models.CASCADE)


class ContextOfViolence(MetaInformationAbstractModel, NameAttributedModels):
    """
    Holds the context of violence
    """


class OtherSubType(MetaInformationAbstractModel, NameAttributedModels):
    """
    Holds the other sub type
    """


class Actor(MetaInformationAbstractModel, NameAttributedModels):
    """
    Conflict related actors
    """
    country = models.ForeignKey('country.Country', verbose_name=_('Country'),
                                null=True,
                                on_delete=models.SET_NULL, related_name='actors')
    # NOTE: torg is used to map actors in the system to it's external source
    torg = models.CharField(verbose_name=_('Torg'), max_length=10, null=True)

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.event.filters import ActorFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id='ID',
            created_at='Created at',
            created_by__full_name='Created by',
            name='Name',
            country__idmc_short_name='Country',
            country__iso3='ISO3',
            torg='TORG',
        )
        data = ActorFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.order_by('id')

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': None,
        }


# Models related to displacement caused by disaster


class DisasterCategory(NameAttributedModels):
    """
    Holds the possible hazard category choices
    """


class DisasterSubCategory(NameAttributedModels):
    """
    Holds the possible hazard sub categories
    """
    category = models.ForeignKey('DisasterCategory', verbose_name=_('Hazard Category'),
                                 related_name='sub_categories', on_delete=models.CASCADE)


class DisasterType(NameAttributedModels):
    """
    Holds the possible hazard types
    """
    disaster_sub_category = models.ForeignKey('DisasterSubCategory',
                                              verbose_name=_('Hazard Sub Category'),
                                              related_name='types', on_delete=models.CASCADE)


class DisasterSubType(NameAttributedModels):
    """
    Holds the possible hazard sub types
    """
    type = models.ForeignKey('DisasterType', verbose_name=_('Hazard Type'),
                             related_name='sub_types', on_delete=models.CASCADE)


class Event(MetaInformationArchiveAbstractModel, models.Model):
    class EVENT_REVIEW_STATUS(enum.Enum):
        REVIEW_NOT_STARTED = 0
        REVIEW_IN_PROGRESS = 1
        APPROVED = 2
        SIGNED_OFF = 3

        __labels__ = {
            REVIEW_NOT_STARTED: _("Review not started"),
            REVIEW_IN_PROGRESS: _("Review in progress"),
            APPROVED: _("Approved"),
            SIGNED_OFF: _("Signed-off"),
        }

    # NOTE figure disaggregation variable definitions
    ND_FIGURES_ANNOTATE = 'total_flow_nd_figures'
    IDP_FIGURES_ANNOTATE = 'total_stock_idp_figures'
    IDP_FIGURES_STOCK_MAX_DATE_ANNOTATE = 'figures_max_end_date'

    crisis = models.ForeignKey('crisis.Crisis', verbose_name=_('Crisis'),
                               blank=True, null=True,
                               related_name='events', on_delete=models.CASCADE)
    name = models.CharField(verbose_name=_('Event Name'), max_length=256)
    event_type = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Event Cause'))

    other_sub_type = models.ForeignKey(
        'OtherSubType', verbose_name=_('Other sub type'),
        blank=True, null=True,
        related_name='events', on_delete=models.SET_NULL)
    glide_numbers = ArrayField(
        models.CharField(
            verbose_name=_('Event Codes'), max_length=256, null=True, blank=True
        ),
        default=list,
        null=True, blank=True
    )
    violence = models.ForeignKey('Violence', verbose_name=_('Violence'),
                                 blank=False, null=True,
                                 related_name='events', on_delete=models.SET_NULL)
    violence_sub_type = models.ForeignKey('ViolenceSubType', verbose_name=_('Violence Sub Type'),
                                          blank=True, null=True,
                                          related_name='events', on_delete=models.SET_NULL)
    actor = models.ForeignKey('Actor', verbose_name=_('Actors'),
                              blank=True, null=True,
                              related_name='events', on_delete=models.SET_NULL)
    # disaster related fields
    disaster_category = models.ForeignKey('DisasterCategory', verbose_name=_('Hazard Category'),
                                          blank=True, null=True,
                                          related_name='events', on_delete=models.SET_NULL)
    disaster_sub_category = models.ForeignKey('DisasterSubCategory', verbose_name=_('Hazard Sub Category'),
                                              blank=True, null=True,
                                              related_name='events', on_delete=models.SET_NULL)
    disaster_type = models.ForeignKey('DisasterType', verbose_name=_('Hazard Type'),
                                      blank=True, null=True,
                                      related_name='events', on_delete=models.SET_NULL)
    disaster_sub_type = models.ForeignKey('DisasterSubType', verbose_name=_('Hazard Sub Type'),
                                          blank=True, null=True,
                                          related_name='events', on_delete=models.SET_NULL)

    countries = models.ManyToManyField('country.Country', verbose_name=_('Countries'),
                                       related_name='events', blank=True)
    start_date = models.DateField(verbose_name=_('Start Date'))
    start_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('Start Date Accuracy'),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    end_date = models.DateField(verbose_name=_('End Date'))
    end_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_('End date accuracy'),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    event_narrative = models.TextField(verbose_name=_('Event Narrative'), null=True)
    osv_sub_type = models.ForeignKey(
        'OsvSubType', verbose_name=_('OSV sub type'),
        blank=True, null=True, related_name='events',
        on_delete=models.SET_NULL
    )
    ignore_qa = models.BooleanField(verbose_name=_('Ignore QA'), default=False)
    context_of_violence = models.ManyToManyField(
        'ContextOfViolence', verbose_name=_('Context of violence'), blank=True, related_name='events'
    )
    assigner = models.ForeignKey(
        'users.User', verbose_name=_('Assigner'), null=True, blank=True,
        related_name='event_assigner', on_delete=models.SET_NULL
    )
    assignee = models.ForeignKey(
        'users.User', verbose_name=_('Assignee'), null=True, blank=True,
        related_name='event_assignee', on_delete=models.SET_NULL
    )
    assigned_at = models.DateTimeField(verbose_name='Assigned at', null=True, blank=True)
    review_status = enum.EnumField(
        EVENT_REVIEW_STATUS,
        verbose_name=_('Event status'),
        default=EVENT_REVIEW_STATUS.REVIEW_NOT_STARTED,
    )
    include_triangulation_in_qa = models.BooleanField(
        verbose_name='Include triangulation in qa?', default=False,
    )

    @classmethod
    def _total_figure_disaggregation_subquery(cls, figures=None):
        if figures is None:
            figures = Figure.objects.all()

        max_stock_end_date_figure_qs = figures.filter(
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            role=Figure.ROLE.RECOMMENDED,
            event=models.OuterRef('pk'),
        ).order_by('-end_date').values('end_date')[:1]

        return {
            cls.IDP_FIGURES_STOCK_MAX_DATE_ANNOTATE: models.Subquery(max_stock_end_date_figure_qs),
            cls.ND_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        event=models.OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    # TODO: what about date range
                    start_date=None,
                    end_date=None,
                ).order_by().values('event').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
            cls.IDP_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures.filter(
                        event=models.OuterRef('pk'),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    start_date=None,
                    end_date=models.OuterRef(cls.IDP_FIGURES_STOCK_MAX_DATE_ANNOTATE),
                ).order_by().values('event').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
        }

    @classmethod
    def annotate_review_figures_count(cls):
        return {
            'review_not_started_count': models.Count(
                'figures',
                filter=models.Q(
                    figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED,
                    figures__role=Figure.ROLE.RECOMMENDED,
                ) | models.Q(
                    figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED,
                    include_triangulation_in_qa=True,
                )
            ),
            'review_in_progress_count': models.Count(
                'figures',
                filter=models.Q(
                    figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS,
                    figures__role=Figure.ROLE.RECOMMENDED,
                ) | models.Q(
                    figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS,
                    include_triangulation_in_qa=True,
                )

            ),
            'review_re_request_count': models.Count(
                'figures',
                filter=models.Q(
                    figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED,
                    figures__role=Figure.ROLE.RECOMMENDED,
                ) | models.Q(
                    figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED,
                    include_triangulation_in_qa=True,
                )

            ),
            'review_approved_count': models.Count(
                'figures',
                filter=models.Q(
                    figures__review_status=Figure.FIGURE_REVIEW_STATUS.APPROVED,
                    figures__role=Figure.ROLE.RECOMMENDED,
                ) | models.Q(
                    figures__review_status=Figure.FIGURE_REVIEW_STATUS.APPROVED,
                    include_triangulation_in_qa=True,
                )

            ),
            'total_count': (
                models.F('review_not_started_count') +
                models.F('review_in_progress_count') +
                models.F('review_re_request_count') +
                models.F('review_approved_count')
            ),
            'progress': models.Case(
                models.When(
                    total_count__gt=0,
                    then=models.F('review_approved_count') / models.F('total_count')
                ),
                default=models.Value(0),
                output_field=models.FloatField()
            )
        }

    # FIXME: this is wrong, this should see event and user not event and figure
    @staticmethod
    def regional_coordinators(event, actor=None):
        actor_regional_coordinators = User.objects.none()
        event_regional_coordinators = User.objects.none()

        if actor:
            actor_regional_coordinators = User.objects.filter(
                portfolios__role=USER_ROLE.REGIONAL_COORDINATOR,
                portfolios__monitoring_sub_region__in=actor.portfolios.values(
                    'monitoring_sub_region'
                )
            )

        if event.countries:
            event_regional_coordinators = User.objects.filter(
                portfolios__role=USER_ROLE.REGIONAL_COORDINATOR,
                portfolios__monitoring_sub_region__in=event.countries.values(
                    'portfolio__monitoring_sub_region'
                )
            )
        coordinators = actor_regional_coordinators | event_regional_coordinators
        return coordinators.values('id')

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.event.filters import EventFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id='ID',
            created_at='Created at',
            created_by__full_name='Created by',
            name='Name',
            start_date='Start date',
            start_date_accuracy='Start date accuracy',
            end_date='End date',
            end_date_accuracy='End date accuracy',
            event_type='Event cause',
            disaster_category__name='Hazard category',
            disaster_sub_category__name='Hazard sub category',
            disaster_type__name='Hazard type',
            disaster_sub_type__name='Hazard sub type',
            disaster_sub_type='Hazard sub type ID',
            countries_iso3='ISO3',
            countries_name='Countries',
            regions_name='Regions',
            figures_count='Figures count',
            entries_count='Entries count',
            # Extra added fields
            old_id='Old ID',
            crisis='Crisis ID',
            crisis__name='Crisis',
            **{
                cls.IDP_FIGURES_ANNOTATE: 'IDPs figure',
                cls.ND_FIGURES_ANNOTATE: 'ND figure',
            },
            other_sub_type__name='Other event sub type',
            violence__name='Violence type',
            violence_sub_type__name='Violence sub type',
            osv_sub_type__name="OSV sub type",
            actor_id='Actor ID',
            actor__name='Actor',
            glide_numbers='Event codes',
            context_of_violences='Context of violences',
        )
        data = EventFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            countries_iso3=StringAgg('countries__iso3', '; ', distinct=True),
            countries_name=StringAgg('countries__idmc_short_name', '; ', distinct=True),
            regions_name=StringAgg('countries__region__name', '; ', distinct=True),
            figures_count=models.Count('figures', distinct=True),
            entries_count=models.Count('figures__entry', distinct=True),
            **cls._total_figure_disaggregation_subquery(),
            context_of_violences=StringAgg('context_of_violence__name', ';', distinct=True),
        ).order_by('created_at')

        def format_glide_numbers(glide_numbers):
            if not glide_numbers:
                return ''
            return get_string_from_list(str(glide_number) for glide_number in glide_numbers)

        def transformer(datum):
            return {
                **datum,
                **dict(
                    start_date_accuracy=getattr(DATE_ACCURACY.get(datum['start_date_accuracy']), 'label', ''),
                    end_date_accuracy=getattr(DATE_ACCURACY.get(datum['end_date_accuracy']), 'label', ''),
                    event_type=getattr(Crisis.CRISIS_TYPE.get(datum['event_type']), 'label', ''),
                    glide_numbers=format_glide_numbers(datum['glide_numbers']),
                )
            }

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': transformer,
        }

    def __str__(self):
        return self.name or str(self.id)

    class Meta:
        permissions = (
            ('assign_event', 'Can assign on event level'),
            ('self_assign_event', 'Can assign self on event level'),
            ('clear_assignee_event', 'Can clear any assignee from event'),
            ('clear_self_assignee_event', 'Can clear self assigned event'),
            ('sign_off_event', 'Can sign-off event'),
        )

    def clone_and_save_event(self, user: 'User'):
        event_data = model_to_dict(
            self,
            exclude=[
                'id', 'created_at', 'created_by', 'last_modified_by',
            ]
        )
        # Clone m2m keys fields
        countries = event_data.pop('countries')
        context_of_violence = event_data.pop('context_of_violence')
        # Clone foreigh key fields
        foreign_key_fields_dict = {
            "crisis": Crisis,
            "violence": Violence,
            "violence_sub_type": ViolenceSubType,
            "actor": Actor,
            "disaster_category": DisasterCategory,
            "disaster_sub_category": DisasterSubCategory,
            "disaster_sub_type": DisasterSubType,
            "disaster_type": DisasterType
        }
        for field, model in foreign_key_fields_dict.items():
            if event_data[field]:
                event_data[field] = model.objects.get(pk=event_data[field])

        event_data['created_by'] = user
        event_data['name'] = add_clone_prefix(event_data['name'])
        cloned_event = Event.objects.create(**event_data)
        # Add m2m contires
        cloned_event.countries.set(countries)
        cloned_event.context_of_violence.set(context_of_violence)
        return cloned_event


class OsvSubType(NameAttributedModels):
    """
    Holds the possible OSV sub types
    """
