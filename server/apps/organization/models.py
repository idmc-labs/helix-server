from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.contrib.models import MetaInformationAbstractModel


class OrganizationKind(MetaInformationAbstractModel, models.Model):
    name = models.CharField(verbose_name=_('Title'), max_length=256)


class Organization(MetaInformationAbstractModel, models.Model):
    name = models.CharField(verbose_name=_('Title'), max_length=512)
    short_name = models.CharField(verbose_name=_('Short Name'), max_length=64,
                                  null=True)
    # logo =
    organization_kind = models.ForeignKey('OrganizationKind', verbose_name=_('Organization Type'),
                                          blank=True, null=True,
                                          on_delete=models.SET_NULL,
                                          related_name='organizations')
    methodology = models.TextField(verbose_name=_('Methodology'))
    source_detail_methodology = models.TextField(_('Source detail and methodology'))
    parent = models.ForeignKey('Organization', verbose_name=_('Organization'),
                               null=True, blank=True,
                               on_delete=models.CASCADE, related_name='sub_organizations')

    def __str__(self):
        return self.name
