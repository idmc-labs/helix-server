from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationAbstractModel, UUIDAbstractModel
from apps.users.roles import ADMIN

User = get_user_model()


class Figure(MetaInformationAbstractModel, UUIDAbstractModel, models.Model):
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

    class TERM(enum.Enum):
        EVACUATED = 0
        DISPLACED = 1
        DESTROYED_HOUSING = 2
        PARTIALLY_DESTROYED_HOUSING = 3
        UNINHABITABLE_HOUSING = 4
        FORCED_TO_FLEE = 5
        HOMELESS = 6
        IN_RELIEF_CAMP = 7
        SHELTERED = 8
        RELOCATED = 9
        AFFECTED = 10
        RETURNS = 11
        MULTIPLE_OR_OTHER = 12

        __labels__ = {
            EVACUATED: _("Evacuated"),
            DISPLACED: _("Displaced"),
            DESTROYED_HOUSING: _("Destroyed housing"),
            PARTIALLY_DESTROYED_HOUSING: _("Partially destroyed housing"),
            UNINHABITABLE_HOUSING: _("Uninhabitable housing"),
            FORCED_TO_FLEE: _("Forced to flee"),
            HOMELESS: _("Homeless"),
            IN_RELIEF_CAMP: _("In relief camp"),
            SHELTERED: _("Sheltered"),
            RELOCATED: _("Relocated"),
            AFFECTED: _("Affected"),
            RETURNS: _("Returns"),
            MULTIPLE_OR_OTHER: _("Multiple/Other"),
        }

    class TYPE(enum.Enum):
        IDP_STOCK = 0

        __labels__ = {
            IDP_STOCK: _("IDP (Stock)"),
        }

    class ROLE(enum.Enum):
        RECOMMENDED = 0
        PARTIAL_ADDED = 1
        PARTIAL_SUBTRACTED = 2
        TRIANGULATION = 3

        __labels__ = {
            RECOMMENDED: _("Recommended figure"),
            PARTIAL_ADDED: _("Partial figure (Added)"),
            PARTIAL_SUBTRACTED: _("Partial figure (Subtracted)"),
            TRIANGULATION: _("Triangulation"),
        }

    entry = models.ForeignKey('Entry', verbose_name=_('Entry'),
                              related_name='figures', on_delete=models.CASCADE)
    district = models.TextField(verbose_name=_('District(s)'))
    town = models.CharField(verbose_name=_('Town/Village'), max_length=256)
    quantifier = enum.EnumField(enum=QUANTIFIER, verbose_name=_('Quantifier'))
    reported = models.PositiveIntegerField(verbose_name=_('Reported Figures'))
    unit = enum.EnumField(enum=UNIT, verbose_name=_('Unit of Figure'), default=UNIT.PERSON)
    household_size = models.PositiveSmallIntegerField(verbose_name=_('Household Size'),
                                                      default=1)
    total_figures = models.PositiveIntegerField(verbose_name=_('Total Figures'), default=0,
                                                editable=False)
    term = enum.EnumField(enum=TERM, verbose_name=_('Term'), default=TERM.EVACUATED)
    type = enum.EnumField(enum=TYPE, verbose_name=_('Figure Type'), default=TYPE.IDP_STOCK)
    role = enum.EnumField(enum=ROLE, verbose_name=_('Role'), default=ROLE.RECOMMENDED)

    start_date = models.DateField(verbose_name=_('Start Date'))
    include_idu = models.BooleanField(verbose_name=_('Include in IDU'))
    excerpt_idu = models.TextField(verbose_name=_('Excerpt for IDU'),
                                   blank=True, null=True)

    is_disaggregated = models.BooleanField(verbose_name=_('Is disaggregated'),
                                           default=False)
    # disaggregation information
    displacement_urban = models.PositiveIntegerField(verbose_name=_('Displacement/Urban'),
                                        blank=True, null=True)
    displacement_rural = models.PositiveIntegerField(verbose_name=_('Displacement/Rural'),
                                        blank=True, null=True)
    location_camp = models.PositiveIntegerField(verbose_name=_('Location/Camp'),
                                       blank=True, null=True)
    location_non_camp = models.PositiveIntegerField(verbose_name=_('Location/Non-Camp'),
                                           blank=True, null=True)
    sex_male = models.PositiveIntegerField(verbose_name=_('Sex/Male'),
                                       blank=True, null=True)
    sex_female = models.PositiveIntegerField(verbose_name=_('Sex/Female'),
                                         blank=True, null=True)
    age_json = ArrayField(base_field=JSONField(verbose_name=_('Age')),
                          verbose_name=_('Age Disaggregation'),
                          blank=True, null=True)
    strata_json = ArrayField(base_field=JSONField(verbose_name=_('Stratum')),
                             verbose_name=_('Strata Disaggregation'),
                             blank=True, null=True)
    # conflict based disaggregation
    conflict = models.PositiveIntegerField(verbose_name=_('Conflict/Conflict'),
                                           blank=True, null=True)
    conflict_political = models.PositiveIntegerField(verbose_name=_('Conflict/Violence-Political'),
                                                     blank=True, null=True)
    conflict_criminal = models.PositiveIntegerField(verbose_name=_('Conflict/Violence-Criminal'),
                                                    blank=True, null=True)
    conflict_communal = models.PositiveIntegerField(verbose_name=_('Conflict/Violence-Communal'),
                                                    blank=True, null=True)
    conflict_other = models.PositiveIntegerField(verbose_name=_('Other'),
                                                 blank=True, null=True)

    @classmethod
    def can_be_created_by(cls, user: User, entry: 'Entry') -> bool:
        return entry.can_be_updated_by(user)

    def can_be_updated_by(self, user: User) -> bool:
        """
        used to check before deleting as well
        """
        return self.entry.can_be_updated_by(user)

    def clean_idu(self) -> OrderedDict:
        errors = OrderedDict()
        if self.include_idu:
            if self.excerpt_idu is None or not self.excerpt_idu.strip():
                errors['excerpt_idu'] = _('This field is required. ')
        return errors

    def clean(self) -> None:
        errors = OrderedDict()
        errors.update(self.clean_idu())
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.total_figures = self.reported
        if self.unit == self.UNIT.HOUSEHOLD:
            self.total_figures = self.reported * self.household_size
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.quantifier.label} {self.reported} {self.term.label}'


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

    def can_be_updated_by(self, user: User) -> bool:
        """
        used to check before deleting as well
        """
        if user.is_superuser \
                or ADMIN in user.groups.values_list('name', flat=True):
            return True
        return self.created_by == user

    def __str__(self):
        return f'Entry {self.article_title}'
