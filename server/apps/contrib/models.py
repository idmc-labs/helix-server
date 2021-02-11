import json
import logging
import uuid
from uuid import uuid4

import boto3
from django.conf import settings

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from utils.fields import CachedFileField

logger = logging.getLogger(__name__)


class UUIDAbstractModel(models.Model):
    uuid = models.UUIDField(verbose_name='UUID', unique=True,
                            blank=True, default=uuid4)

    class Meta:
        abstract = True


class ArchiveAbstractModel(models.Model):
    old_id = models.CharField(verbose_name=_('Old primary key'), max_length=32,
                              null=True, blank=True)

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


class MetaInformationArchiveAbstractModel(ArchiveAbstractModel, MetaInformationAbstractModel):
    class Meta:
        abstract = True


def attachment_upload_to(instance: 'Attachment', filename: str) -> 'str':
    return (f'attachments'
            f'/{Attachment.FOR_CHOICES.get(getattr(instance, "attachment_for", "unknowns")).name}'
            f'/{filename}')


class Attachment(MetaInformationAbstractModel):
    class FOR_CHOICES(enum.Enum):
        ENTRY = 0
        COMMUNICATION = 1
        CONTEXTUAL_UPDATE = 2

    attachment = CachedFileField(verbose_name=_('Attachment'),
                                 blank=False, null=False,
                                 upload_to=attachment_upload_to)
    attachment_for = enum.EnumField(enum=FOR_CHOICES, verbose_name=_('Attachment for'),
                                    null=True, blank=True,
                                    help_text=_('The type of instance for which attachment was'
                                                ' uploaded for'))
    mimetype = models.CharField(verbose_name=_('Mimetype'), max_length=256,
                                blank=True, null=True)
    encoding = models.CharField(verbose_name=_('Encoding'), max_length=256,
                                blank=True, null=True)
    filetype_detail = models.CharField(verbose_name=_('File type detail'), max_length=256,
                                       blank=True, null=True)


class SoftDeleteQueryset(models.QuerySet):
    def delete(self):
        self.update(deleted_on=timezone.now())


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQueryset(self.model, using=self._db).filter(deleted_on__isnull=True)


class SoftDeleteModel(models.Model):
    deleted_on = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    _objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.deleted_on = timezone.now()
        self.save()
        return self

    def undelete(self, *args, **kwargs):
        self.deleted_on = None
        self.save()
        return self

    class Meta:
        abstract = True


class SourcePreview(MetaInformationAbstractModel):
    PREVIEW_FOLDER = 'source/previews'

    url = models.URLField(verbose_name=_('Source URL'), max_length=2000)
    token = models.CharField(verbose_name=_('Token'),
                             max_length=64, db_index=True,
                             blank=True, null=True)
    pdf = CachedFileField(verbose_name=_('Rendered Pdf'),
                          blank=True, null=True,
                          upload_to=PREVIEW_FOLDER)
    completed = models.BooleanField(default=False)
    reason = models.TextField(verbose_name=_('Error Reason'),
                              blank=True, null=True)

    @classmethod
    def get_pdf(cls, url: str, instance: 'SourcePreview' = None, **kwargs) -> 'SourcePreview':
        """
        Based on the url, generate a pdf and store it.
        """
        if not instance:
            token = str(uuid.uuid4())
            instance = cls(token=token)
        instance.url = url
        # TODO: remove .pdf in production... this will happen after webhook
        instance.pdf = cls.PREVIEW_FOLDER + '/' + instance.token + '.pdf'

        instance.save()

        payload = dict(
            url=url,
            token=instance.token,
            filename=f'{instance.token}.pdf',
        )
        logger.info(f'Invoking lambda function for preview {url} {instance.token}')
        client = boto3.client('lambda')
        client.invoke(
            FunctionName=settings.LAMBDA_HTML_TO_PDF,
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        return instance
