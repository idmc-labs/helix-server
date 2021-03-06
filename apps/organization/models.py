from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.contrib.models import MetaInformationArchiveAbstractModel, SoftDeleteModel


class OrganizationKind(MetaInformationArchiveAbstractModel, models.Model):
    name = models.CharField(verbose_name=_('Title'), max_length=256)

    def __str__(self):
        return self.name


class Organization(MetaInformationArchiveAbstractModel,
                   SoftDeleteModel,
                   models.Model):
    name = models.CharField(verbose_name=_('Title'), max_length=512)
    short_name = models.CharField(verbose_name=_('Short Name'), max_length=64,
                                  null=True)
    # logo =
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
