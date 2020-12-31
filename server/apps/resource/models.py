from typing import Tuple

from django.db import models
from django.db.models import ProtectedError
from django.utils.translation import gettext, gettext_lazy as _

from apps.contrib.models import MetaInformationArchiveAbstractModel


class ResourceGroup(MetaInformationArchiveAbstractModel):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    def is_deletable(self) -> bool:
        if res := self.resources.count():
            raise ProtectedError(gettext(f'There are {res} resource(s) '
                                         f'associated to this group. '
                                         f'Please delete them first'), [])
        return True

    def can_delete(self, *args, **kwargs) -> Tuple[bool, str]:
        try:
            self.is_deletable()
        except ProtectedError as e:
            return False, e.args[0]
        return True, ''

    def __str__(self):
        return self.name


class Resource(MetaInformationArchiveAbstractModel):
    name = models.CharField(verbose_name=_('Name'), max_length=256)
    url = models.URLField(verbose_name=_('URL'), max_length=256)
    group = models.ForeignKey('ResourceGroup', verbose_name=_('Resource Group'),
                              related_name='resources', on_delete=models.SET_NULL,
                              blank=True, null=True)
    countries = models.ManyToManyField('country.Country', verbose_name=_('Countries'),
                                       related_name='+', blank=False)
    last_accessed_on = models.DateTimeField(verbose_name=_('Last Accessed On'),
                                            blank=True, null=True)

    def __str__(self):
        return self.name
