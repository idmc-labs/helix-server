from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel, SoftDeleteModel


class OrganizationKind(MetaInformationArchiveAbstractModel, models.Model):
    name = models.CharField(verbose_name=_('Title'), max_length=256)

    def __str__(self):
        return self.name


class Organization(MetaInformationArchiveAbstractModel,
                   SoftDeleteModel,
                   models.Model):
    class ORGANIZATION_CATEGORY(enum.Enum):
        EMPTY = 0
        REGIONAL = 1
        INTERNATIONAL = 2

        __labels__ = {
            EMPTY: _(""),
            REGIONAL: _("Regional"),
            INTERNATIONAL: _("International"),
        }
    name = models.CharField(verbose_name=_('Title'), max_length=512)
    short_name = models.CharField(verbose_name=_('Short Name'), max_length=64,
                                  null=True)
    category = enum.EnumField(ORGANIZATION_CATEGORY, verbose_name=_('Crisis Type'),
                              default=ORGANIZATION_CATEGORY.EMPTY)
    countries = models.ManyToManyField('country.Country', verbose_name=_('Countries'),
                                       related_name='organizations')
    organization_kind = models.ForeignKey('OrganizationKind', verbose_name=_('Organization Type'),
                                          blank=True, null=True,
                                          on_delete=models.SET_NULL,
                                          related_name='organizations')
    methodology = models.TextField(verbose_name=_('Methodology'), blank=True, null=True)
    breakdown = models.TextField(verbose_name=_('Source Breakdown and Reliability'), blank=True, null=True)
    parent = models.ForeignKey('Organization', verbose_name=_('Organization'),
                               null=True, blank=True,
                               on_delete=models.CASCADE, related_name='sub_organizations')

    def __str__(self):
        return self.name
