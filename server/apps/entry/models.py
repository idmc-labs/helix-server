from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel
from apps.users.roles import ADMIN


class SubFigure(models.Model):
    figure = models.ForeignKey('Figure', verbose_name=_('Figure'),
                               related_name='sub_figures', on_delete=models.CASCADE)
    # source = models.
    # destination

    class Meta:
        abstract = True


class Figure(MetaInformationAbstractModel, models.Model):
    class QUANTIFIER(enum.Enum):
        more_than = 0
        less_than = 1
        exact = 2

    class UNIT(enum.Enum):
        person = 0

    class TERM(enum.Enum):
        evacuated = 0

    class TYPE(enum.Enum):
        idp_stock = 0

    class ROLE(enum.Enum):
        recommended = 0

    entry = models.ForeignKey('Entry', verbose_name=_('Entry'),
                              related_name='figures', on_delete=models.CASCADE)
    district = models.TextField(verbose_name=_('District(s)'))
    town = models.CharField(verbose_name=_('Town/Village'), max_length=256)
    quantifier = enum.EnumField(enum=QUANTIFIER, verbose_name=_('Quantifier'))
    reported = models.PositiveIntegerField(verbose_name=_('Reported Figures'))
    unit = enum.EnumField(enum=UNIT, verbose_name=_('Unit of Figure'), default=UNIT.person)
    term = enum.EnumField(enum=TERM, verbose_name=_('Term'), default=TERM.evacuated)
    type = enum.EnumField(enum=TYPE, verbose_name=_('Figure Type'), default=TYPE.idp_stock)
    role = enum.EnumField(enum=ROLE, verbose_name=_('Role'), default=ROLE.recommended)

    start_date = models.DateField(verbose_name=_('Start Date'))
    include_idu = models.BooleanField(verbose_name=_('Include in IDU'))
    excerpt_idu = models.TextField(verbose_name=_('Excerpt for IDU'))

    def __str__(self):
        return f'{self.quantifier} {self.reported} {self.term}'


class Entry(MetaInformationAbstractModel, models.Model):
    url = models.URLField(verbose_name=_('Source URL'),
                          blank=True, null=True)
    # document todo
    article_title = models.TextField(verbose_name=_('Article Title'))
    source = models.CharField(verbose_name=_('Source'), max_length=256)
    publisher = models.CharField(verbose_name=_('Publisher'), max_length=256)
    publish_date = models.DateField(verbose_name=_('Published Date'))
    source_methodology = models.TextField(verbose_name=_('Source Methodology'),
                                          blank=True, null=True)
    source_excerpt = models.TextField(verbose_name=_('Excerpt from Source'),
                                      blank=True, null=True)
    source_breakdown = models.TextField(verbose_name=_('Source Breakdown and Reliability'),
                                        blank=True, null=True)
    event = models.ForeignKey('event.Event', verbose_name=_('Event'),
                              related_name='entries', on_delete=models.CASCADE)

    idmc_analysis = models.TextField(verbose_name=_('IDMC Analysis'),
                                     blank=False, null=True)
    methodology = models.TextField(verbose_name=_('Methodology'),
                                   blank=False, null=True)
    # grid todo
    tags = ArrayField(base_field=models.CharField(verbose_name=_('Tag'), max_length=32),
                      blank=True, null=True)

    reviewers = models.ManyToManyField('users.User', verbose_name=_('Reviewers'),
                                       blank=True,
                                       related_name='review_entries')

    def can_be_updated_by(self, user: 'User') -> bool:
        """
        used to check before deleting as well
        """
        if ADMIN in user.groups.values_list('name', flat=True):
            return True
        return self.created_by == user

    def __str__(self):
        return f'Entry {self.article_title}'
