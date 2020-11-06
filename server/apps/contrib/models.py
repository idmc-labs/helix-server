from uuid import uuid4

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from utils.fields import CachedFileField


class UUIDAbstractModel(models.Model):
    uuid = models.UUIDField(verbose_name='UUID', unique=True,
                            blank=True, default=uuid4)

    class Meta:
        abstract = True


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


class Attachment(MetaInformationAbstractModel):
    ATTACHMENT_FOLDER = 'attachments'

    class FOR_CHOICES(enum.Enum):
        ENTRY = 0
        COMMUNICATION = 1

    attachment = CachedFileField(verbose_name=_('Attachment'),
                                 blank=False, null=False,
                                 upload_to=ATTACHMENT_FOLDER)
    attachment_for = enum.EnumField(enum=FOR_CHOICES, verbose_name=_('Attachment for'), null=True, blank=True, help_text=_('The type of instance for which attachment was uploaded for'))

