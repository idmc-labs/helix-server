from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel


class Review(MetaInformationArchiveAbstractModel, models.Model):
    UNIQUE_TOGETHER_FIELDS = {'entry', 'figure', 'field', 'age_id', 'strata_id'}
    UNIQUE_TOGETHER_WITHOUT_ENTRY_FIELDS = UNIQUE_TOGETHER_FIELDS - {'entry'}

    class ENTRY_REVIEW_STATUS(enum.Enum):
        RED = 0
        GREEN = 1
        GREY = 2

        __labels__ = {
            RED: _("Red"),
            GREEN: _("Green"),
            GREY: _("Grey"),
        }

    entry = models.ForeignKey('entry.Entry', verbose_name=_('Entry'),
                              related_name='reviews', on_delete=models.CASCADE)
    figure = models.ForeignKey('entry.Figure', verbose_name=_('Figure'),
                               blank=True, null=True,
                               related_name='figure_reviews', on_delete=models.SET_NULL)
    field = models.CharField(verbose_name=_('Field'), max_length=256)
    value = enum.EnumField(enum=ENTRY_REVIEW_STATUS, default=ENTRY_REVIEW_STATUS.GREY.value)
    age_id = models.CharField(verbose_name=_('Age ID'), max_length=256,
                              null=True, blank=True)
    strata_id = models.CharField(verbose_name=_('Strata ID'), max_length=256,
                                 null=True, blank=True)
    geo_location = models.ForeignKey('entry.OSMName', verbose_name=_('Geolocation/OSM'),
                                     null=True, blank=True,
                                     related_name='reviews', on_delete=models.SET_NULL)
    comment = models.ForeignKey('review.ReviewComment', verbose_name=_('Comment'),
                                blank=True, null=True,
                                related_name='reviews', on_delete=models.CASCADE)


class ReviewComment(MetaInformationArchiveAbstractModel, models.Model):
    body = models.TextField(verbose_name=_('Body'), null=True)
    entry = models.ForeignKey('entry.Entry', verbose_name=_('Entry'),
                              related_name='review_comments', on_delete=models.CASCADE)
