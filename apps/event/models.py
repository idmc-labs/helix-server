from collections import OrderedDict

from django.db import models
from django.utils.translation import gettext_lazy as _, gettext
from django_enumfield import enum

from apps.contrib.models import (
    MetaInformationAbstractModel,
    MetaInformationArchiveAbstractModel,
)
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from utils.validations import is_child_parent_dates_valid


class NameAttributedModels(models.Model):
    name = models.CharField(_('Name'), max_length=256)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


# Models related to displacement caused by conflict


class Trigger(NameAttributedModels):
    """
    Holds the possible trigger choices
    """


class TriggerSubType(NameAttributedModels):
    """
    Holds the possible trigger sub types
    """


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


class Actor(MetaInformationAbstractModel, NameAttributedModels):
    """
    Conflict related actors
    """
    country = models.ForeignKey('country.Country', verbose_name=_('Country'),
                                null=True,
                                on_delete=models.SET_NULL, related_name='actors')
    # NOTE: torg is used to map actors in the system to it's external source
    torg = models.CharField(verbose_name=_('Torg'), max_length=10, null=True)


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
    class EVENT_OTHER_SUB_TYPE(enum.Enum):
        DEVELOPMENT = 0
        EVICTION = 1
        TECHNICAL_DISASTER = 2
        # TODO: add more based on IDMC inputs

        __labels__ = {
            DEVELOPMENT: _('Development'),
            EVICTION: _('Eviction'),
            TECHNICAL_DISASTER: _('Technical disaster'),
        }

    crisis = models.ForeignKey('crisis.Crisis', verbose_name=_('Crisis'),
                               blank=True, null=True,
                               related_name='events', on_delete=models.CASCADE)
    name = models.CharField(verbose_name=_('Event Name'), max_length=256)
    event_type = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Event Type'))
    other_sub_type = enum.EnumField(EVENT_OTHER_SUB_TYPE, verbose_name=_('Other subtypes'),
                                    blank=True, null=True)
    glide_number = models.CharField(verbose_name=_('Glide Number'), max_length=256,
                                    null=True, blank=True)
    # conflict related fields
    trigger = models.ForeignKey('Trigger', verbose_name=_('Trigger'),
                                blank=True, null=True,
                                related_name='events', on_delete=models.SET_NULL)
    trigger_sub_type = models.ForeignKey('TriggerSubType', verbose_name=_('Trigger Sub-Type'),
                                         blank=True, null=True,
                                         related_name='events', on_delete=models.SET_NULL)
    violence = models.ForeignKey('Violence', verbose_name=_('Violence'),
                                 blank=True, null=True,
                                 related_name='events', on_delete=models.SET_NULL)
    violence_sub_type = models.ForeignKey('ViolenceSubType', verbose_name=_('Violence Sub-Type'),
                                          blank=True, null=True,
                                          related_name='events', on_delete=models.SET_NULL)
    actor = models.ForeignKey('Actor', verbose_name=_('Actors'),
                              blank=True, null=True,
                              related_name='events', on_delete=models.SET_NULL)
    # disaster related fields
    disaster_category = models.ForeignKey('DisasterCategory', verbose_name=_('Disaster Category'),
                                          blank=True, null=True,
                                          related_name='events', on_delete=models.SET_NULL)
    disaster_sub_category = models.ForeignKey('DisasterSubCategory', verbose_name=_('Disaster Sub-Type'),
                                              blank=True, null=True,
                                              related_name='events', on_delete=models.SET_NULL)
    disaster_type = models.ForeignKey('DisasterType', verbose_name=_('Disaster Type'),
                                      blank=True, null=True,
                                      related_name='events', on_delete=models.SET_NULL)
    disaster_sub_type = models.ForeignKey('DisasterSubType', verbose_name=_('Disaster Sub-Type'),
                                          blank=True, null=True,
                                          related_name='events', on_delete=models.SET_NULL)

    countries = models.ManyToManyField('country.Country', verbose_name=_('Countries'),
                                       related_name='events', blank=True)
    start_date = models.DateField(verbose_name=_('Start Date'),
                                  blank=True, null=True)
    end_date = models.DateField(verbose_name=_('End Date'),
                                blank=True, null=True)
    event_narrative = models.TextField(verbose_name=_('Event Narrative'),
                                       null=True, blank=True)

    @property
    def total_stock_figures(self) -> int:
        filters = dict(event=self.id)
        return Figure.get_total_stock_figure(filters)

    @property
    def total_flow_figures(self) -> int:
        filters = dict(event=self.id)
        return Figure.get_total_flow_figure(filters)

    @staticmethod
    def clean_dates(values: dict, instance=None) -> OrderedDict:
        return is_child_parent_dates_valid(values, instance, 'crisis')

    @staticmethod
    def clean_by_event_type(values: dict, instance=None) -> OrderedDict:
        errors = OrderedDict()
        event_type = values.get('event_type', getattr(instance, 'event_type', None))
        if event_type == Crisis.CRISIS_TYPE.CONFLICT:
            if not values.get('violence_sub_type', getattr(instance, 'violence_sub_type', None)):
                errors['violence_sub_type'] = gettext('Please mention at least'
                                                      ' the reason for violence.')
        elif event_type == Crisis.CRISIS_TYPE.DISASTER:
            if not values.get('disaster_sub_type', getattr(instance, 'disaster_sub_type', None)):
                errors['disaster_sub_type'] = gettext('Please mention the sub-type of disaster. ')
        return errors

    def save(self, *args, **kwargs):
        if self.disaster_sub_type:
            self.disaster_type = self.disaster_sub_type.type
            self.disaster_sub_category = self.disaster_type.disaster_sub_category
            self.disaster_category = self.disaster_sub_category.category
        if self.violence_sub_type:
            self.violence = self.violence_sub_type.violence
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name or str(self.id)
