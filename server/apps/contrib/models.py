from uuid import uuid4

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UUIDAbstractModel(models.Model):
    uuid = models.UUIDField(verbose_name='UUID', unique=True,
                            blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.uuid:
            # if we didnt receive uuid from the client or is not pre-populated
            while True:
                temp = uuid4()
                if not self.__class__._default_manager.filter(uuid=self.uuid).exists():
                    break
            self.uuid = temp
        return super().save(*args, **kwargs)


class MetaInformationAbstractModel(models.Model):
    created_at = models.DateTimeField(verbose_name=_('Created At'), default=timezone.now)
    modified_at = models.DateTimeField(verbose_name=_('Modified At'), auto_now=True)
    created_by = models.ForeignKey('users.User', verbose_name=_('Created By'),
                                   blank=True, null=True,
                                   related_name='created_%(class)s', on_delete=models.SET_NULL)
    last_modified_by = models.ForeignKey('users.User', verbose_name=_('Last Modified By'),
                                         blank=True, null=True,
                                         related_name='+', on_delete=models.SET_NULL)
    version_id = models.CharField(verbose_name=_('Version'), max_length=16,
                                  blank=True, null=True)

    class Meta:
        abstract = True
