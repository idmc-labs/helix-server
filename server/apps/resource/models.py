from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.contrib.models import MetaInformationAbstractModel


class ResourceGroup(MetaInformationAbstractModel):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    def __str__(self):
        return self.name


class Resource(MetaInformationAbstractModel):
    name = models.CharField(verbose_name=_('Name'), max_length=256)
    url = models.URLField(verbose_name=_('URL'), max_length=256)
    group = models.ForeignKey('ResourceGroup',
                              related_name='resources', on_delete=models.PROTECT)
    last_accessed_on = models.DateTimeField(verbose_name=_('Last Accessed On'),
                                            blank=True, null=True)

    def __str__(self):
        return self.name
