from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel


class Review(MetaInformationAbstractModel, models.Model):
    class REVIEW_STATUS(enum.Enum):
        RED = 0
        GREEN = 1

        __labels__ = {
            RED: _("Red"),
            GREEN: _("Green"),
        }

    entry = models.ForeignKey('entry.Entry', verbose_name=_('Entry'),
                              related_name='reviews', on_delete=models.CASCADE)
    figure = models.ForeignKey('entry.Figure', verbose_name=_('Figure'),
                               blank=True, null=True,
                               related_name='figure_reviews', on_delete=models.SET_NULL)
    field = models.CharField(verbose_name=_('Field'), max_length=256)
    value = enum.EnumField(verbose_name=_('Review Status'), enum=REVIEW_STATUS)
    age_id = models.CharField(verbose_name=_('Age ID'), max_length=256,
                              null=True, blank=True)
    strata_id = models.CharField(verbose_name=_('Strata ID'), max_length=256,
                                 null=True, blank=True)
    comment = models.ForeignKey('review.ReviewComment', verbose_name=_('Comment'),
                                blank=True, null=True,
                                related_name='reviews', on_delete=models.CASCADE)


class ReviewComment(MetaInformationAbstractModel, models.Model):
    body = models.TextField(verbose_name=_('Body'))
    entry = models.ForeignKey('entry.Entry', verbose_name=_('Entry'),
                              related_name='review_comments', on_delete=models.CASCADE)
