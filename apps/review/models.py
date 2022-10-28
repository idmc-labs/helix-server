from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
from apps.contrib.models import MetaInformationArchiveAbstractModel


class UnifiedReviewComment(MetaInformationArchiveAbstractModel, models.Model):

    class ReviewCommentStatus(enum.Enum):
        RED = 0
        GREEN = 1
        GREY = 2

        __labels__ = {
            RED: _("Red"),
            GREEN: _("Green"),
            GREY: _("Grey"),
        }

    class ReviewFieldType(enum.Enum):
        # Figure fields
        FIGURE_SOURCE_EXCERPT = 0
        FIGURE_ANALYSIS_CAVEATS_AND_CALCULATION_LOGIC = 1
        FIGURE_SOURCES = 2
        FIGURE_ROLE = 3
        FIGURE_DISPLACEMENT_OCCURRED = 4
        FIGURE_TERM = 5
        FIGURE_REPORTED_FIGURE = 6
        FIGURE_CATEGORY = 7
        FIGURE_START_DATE = 8
        FIGURE_END_DATE = 9
        FIGURE_STOCK_DATE = 10
        FIGURE_STOCK_REPORTING_DATE = 11
        FIGURE_MAIN_TRIGGER_OF_REPORTED_FIGURE = 12
        FIGURE_COUNTRY = 13

        # Location fields
        LOCATION_TYPE = 114
        LOCATION_ACCURACY = 115

        __labels__ = {
            FIGURE_SOURCE_EXCERPT: 'Source Excerpt',
            FIGURE_ANALYSIS_CAVEATS_AND_CALCULATION_LOGIC: 'Analysis, Caveats And Calculation Logic',
            FIGURE_SOURCES: 'Sources',
            FIGURE_ROLE: 'Role',
            FIGURE_DISPLACEMENT_OCCURRED: 'Displacement Occurred',
            FIGURE_TERM: 'Term',
            FIGURE_REPORTED_FIGURE: 'Reported Figure',
            FIGURE_CATEGORY: 'Category',
            FIGURE_START_DATE: 'Start Date',
            FIGURE_END_DATE: 'End Date',
            FIGURE_STOCK_DATE: 'Stock Date',
            FIGURE_STOCK_REPORTING_DATE: 'Stock Reporting Date',
            FIGURE_MAIN_TRIGGER_OF_REPORTED_FIGURE: 'Main Trigger Of Reported Figure',
            FIGURE_COUNTRY: 'Country',
            LOCATION_TYPE: 'Location type',
            LOCATION_ACCURACY: 'Location accuracy',
        }

    # TODO: Make event non nullable field after review data migration
    event = models.ForeignKey(
        'event.Event', verbose_name=_('Event'),
        related_name='event_reviews', on_delete=models.SET_NULL, null=True, blank=True
    )
    geo_location = models.ForeignKey(
        'entry.OSMname', verbose_name=_('Geo location'), null=True, blank=True,
        related_name='geo_location_reviews', on_delete=models.SET_NULL
    )
    figure = models.ForeignKey(
        'entry.Figure', verbose_name=_('Figure'),
        blank=True, null=True,
        related_name='figure_review_comments', on_delete=models.SET_NULL
    )
    field = enum.EnumField(enum=ReviewFieldType, null=True, blank=True)
    comment_type = enum.EnumField(enum=ReviewCommentStatus, default=ReviewCommentStatus.GREY.value)
    geo_location = models.ForeignKey(
        'entry.OSMName', verbose_name=_('Geolocation/OSM'),
        null=True, blank=True,
        related_name='geo_location_review_comments', on_delete=models.SET_NULL
    )
    comment = models.TextField(
        verbose_name=_('Comment'),
        blank=True, null=True,
    )
    is_edited = models.BooleanField(verbose_name=_('Is edited?'), default=False)
    is_deleted = models.BooleanField(verbose_name=_('Is deleted?'), default=False)


class Review(MetaInformationArchiveAbstractModel, models.Model):
    '''
    NOTE: Add to UNIQUE_TOGETHER_FIELDS if you add a new field to this model, if required
    '''
    UNIQUE_TOGETHER_FIELDS = {'entry', 'figure', 'field', 'age', 'geo_location'}
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
    age = models.CharField(verbose_name=_('Age'), max_length=256,
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
