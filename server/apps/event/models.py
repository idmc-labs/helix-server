from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel
from apps.crisis.models import Crisis


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
    trigger = models.ForeignKey('Trigger',
                                related_name='sub_types', on_delete=models.CASCADE)


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


class Actor(NameAttributedModels):
    """
    Conflict related actors
    """
    # country = todo


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
    disaster_sub_category = models.ForeignKey('DisasterSubCategory', verbose_name=_('Disaster Sub Category'),
                                              related_name='types', on_delete=models.CASCADE)


class DisasterSubType(NameAttributedModels):
    """
    Holds the possible disaster sub types
    """
    type = models.ForeignKey('DisasterType', verbose_name=_('Disaster Sub Type'),
                             related_name='sub_types', on_delete=models.CASCADE)


class Event(MetaInformationAbstractModel, models.Model):
    crisis = models.ForeignKey('crisis.Crisis', verbose_name=_('Crisis'),
                               related_name='events', on_delete=models.CASCADE)
    name = models.CharField(verbose_name=_('Event Name'), max_length=256)
    event_type = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Event Type'))
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

    @staticmethod
    def clean_dates(values: dict, instance=None) -> OrderedDict:
        errors = OrderedDict()
        start_date = values.get('start_date', getattr(instance, 'start_date', None))
        end_date = values.get('end_date', getattr(instance, 'end_date', None))
        if start_date and end_date and end_date < start_date:
            errors['end_date'] = _('Pick the end date later than start date. ')
        return errors

    @staticmethod
    def clean_by_event_type(values: dict, instance=None) -> OrderedDict:
        errors = OrderedDict()
        event_type = values.get('event_type', getattr(instance, 'event_type', None))
        if event_type == Crisis.CRISIS_TYPE.CONFLICT:
            if not values.get('violence', getattr(instance, 'violence', None)):
                errors['violence'] = _('Please mention at least the reason for violence. ')
        elif event_type == Crisis.CRISIS_TYPE.DISASTER:
            if not values.get('disaster_category', getattr(instance, 'disaster_category', None)):
                errors['disaster_category'] = _('Please mention at least the category of disaster. ')
            if not values.get('glide_number', getattr(instance, 'glide_number', None)):
                errors['glide_number'] = _('Glide Number is required. ')
        return errors

    def __str__(self):
        return self.name
