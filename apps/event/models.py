from collections import OrderedDict

from django.db import models
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django_enumfield import enum

from apps.contrib.models import (
    MetaInformationAbstractModel,
    MetaInformationArchiveAbstractModel,
)
from apps.crisis.models import Crisis
from apps.contrib.commons import DATE_ACCURACY
from apps.entry.models import Figure
from apps.users.models import User
from django.contrib.postgres.fields import ArrayField
from django.forms import model_to_dict
from utils.common import add_clone_prefix
from apps.common.enums import EVENT_OTHER_SUB_TYPE


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
            id='Id',
            created_at='Created At',
            created_by__full_name='Created By',
            name='Name',
            country__name='Country',
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
    Holds the possible disaster category choices
    """


class DisasterSubCategory(NameAttributedModels):
    """
    Holds the possible disaster sub categories
    """
    category = models.ForeignKey('DisasterCategory', verbose_name=_('Disaster Category'),
                                 related_name='sub_categories', on_delete=models.CASCADE)


class DisasterType(NameAttributedModels):
    """
    Holds the possible disaster types
    """
    disaster_sub_category = models.ForeignKey('DisasterSubCategory',
                                              verbose_name=_('Disaster Sub Category'),
                                              related_name='types', on_delete=models.CASCADE)


class DisasterSubType(NameAttributedModels):
    """
    Holds the possible disaster sub types
    """
    type = models.ForeignKey('DisasterType', verbose_name=_('Disaster Type'),
                             related_name='sub_types', on_delete=models.CASCADE)


class Event(MetaInformationArchiveAbstractModel, models.Model):
    # NOTE figure disaggregation variable definitions
    ND_FIGURES_ANNOTATE = 'total_flow_nd_figures'
    IDP_FIGURES_ANNOTATE = 'total_stock_idp_figures'
    crisis = models.ForeignKey('crisis.Crisis', verbose_name=_('Crisis'),
                               blank=True, null=True,
                               related_name='events', on_delete=models.CASCADE)
    name = models.CharField(verbose_name=_('Event Name'), max_length=256)
    event_type = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Event Cause'))
    other_sub_type = enum.EnumField(EVENT_OTHER_SUB_TYPE, verbose_name=_('Other Event Sub Types'),
                                    blank=True, null=True)
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
    disaster_category = models.ForeignKey('DisasterCategory', verbose_name=_('Disaster Category'),
                                          blank=True, null=True,
                                          related_name='events', on_delete=models.SET_NULL)
    disaster_sub_category = models.ForeignKey('DisasterSubCategory', verbose_name=_('Disaster Sub Category'),
                                              blank=True, null=True,
                                              related_name='events', on_delete=models.SET_NULL)
    disaster_type = models.ForeignKey('DisasterType', verbose_name=_('Disaster Type'),
                                      blank=True, null=True,
                                      related_name='events', on_delete=models.SET_NULL)
    disaster_sub_type = models.ForeignKey('DisasterSubType', verbose_name=_('Disaster Sub Type'),
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

    @classmethod
    def _total_figure_disaggregation_subquery(cls, figures=None):
        figures = figures or Figure.objects.all()

        return {
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
                    reference_point=timezone.now().date(),
                ).order_by().values('event').annotate(
                    _total=models.Sum('total_figures')
                ).values('_total')[:1],
                output_field=models.IntegerField()
            ),
        }

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.event.filters import EventFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            old_id='Old Id',
            id='Id',
            created_at='Created At',
            created_by__full_name='Created By',
            crisis='Crisis Id',
            crisis__name='Crisis',
            name='Name',
            start_date='Start Date',
            start_date_accuracy='Start Date Accuracy',
            end_date='End Date',
            end_date_accuracy='End Date Accuracy',
            countries_iso3='ISO3',
            countries_name='Countries',
            regions_name='Regions',
            figures_count='Figures Count',
            entries_count='Entries Count',
            **{
                cls.IDP_FIGURES_ANNOTATE: 'IDPs Figure',
                cls.ND_FIGURES_ANNOTATE: 'ND Figure',
            },
            event_type='Event Cause',
            other_sub_type='Other Event Sub Type',
            violence__name='Violence',
            violence_sub_type__name='Violence Sub Type',
            osv_sub_type__name="OSV Sub Type",
            actor_id='Actor Id',
            actor__name='Actor',
            disaster_category__name='Disaster Category',
            disaster_sub_category__name='Disaster Sub Category',
            disaster_type__name='Disaster Type',
            disaster_sub_type__name='Disaster Sub Type',
            disaster_sub_type='Diaster Sub Type Id',
            glide_numbers='Event Codes',
            context_of_violence__name='Context of violences',
        )
        data = EventFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            countries_iso3=ArrayAgg('countries__iso3', distinct=True),
            countries_name=ArrayAgg('countries__name', distinct=True),
            regions_name=ArrayAgg('countries__region__name', distinct=True),
            figures_count=models.Count('figures', distinct=True),
            entries_count=models.Count('figures__entry', distinct=True),
            **cls._total_figure_disaggregation_subquery(),
        ).order_by('-created_at').select_related(
            'violence',
            'violence_sub_type',
            'actor',
            'disaster_category',
            'disaster_sub_category',
            'disaster_type',
            'disaster_sub_type',
            'created_at',
            'osv_sub_type'
        ).prefetch_related(
            'countries',
        )

        def transformer(datum):
            return {
                **datum,
                **dict(
                    start_date_accuracy=getattr(DATE_ACCURACY.get(datum['start_date_accuracy']), 'name', ''),
                    end_date_accuracy=getattr(DATE_ACCURACY.get(datum['end_date_accuracy']), 'name', ''),
                    event_type=getattr(Crisis.CRISIS_TYPE.get(datum['event_type']), 'name', ''),
                    other_sub_type=getattr(EVENT_OTHER_SUB_TYPE.get(datum['other_sub_type']), 'name', ''),
                )
            }

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': transformer,
        }

    def save(self, *args, **kwargs):
        if self.disaster_sub_type:
            self.disaster_type = self.disaster_sub_type.type
            self.disaster_sub_category = self.disaster_type.disaster_sub_category
            self.disaster_category = self.disaster_sub_category.category
        else:
            self.disaster_type = None
            self.disaster_sub_category = None
            self.disaster_category = None

        if self.violence_sub_type:
            self.violence = self.violence_sub_type.violence
        else:
            self.violence = None
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name or str(self.id)

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
