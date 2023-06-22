import logging
import uuid
from uuid import uuid4
from collections import OrderedDict

from django.apps import apps
from django.db.models import JSONField
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.tasks import generate_excel_file
from apps.users.models import User
from apps.entry.tasks import generate_pdf
from utils.fields import CachedFileField
from apps.contrib.redis_client_track import set_client_ids_in_redis

logger = logging.getLogger(__name__)


def global_upload_to(instance, filename: str) -> str:
    return f'contrib/{instance.__class__.__name__.lower()}/{uuid4()}/{uuid4()}/{filename}'


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


class Attachment(MetaInformationAbstractModel):
    ALLOWED_MIMETYPES = (
        # text
        'application/x-abiword', 'text/csv', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/epub+zip',
        'application/vnd.oasis.opendocument.presentation',
        'application/vnd.oasis.opendocument.spreadsheet', 'application/vnd.oasis.opendocument.text', 'application/pdf',
        'application/xml', 'text/xml', 'application/vnd.ms-powerpoint', 'application/xhtml+xml', 'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/rtf', 'text/javascript',
        'text/html', 'text/calendar', 'text/plain',
        # image
        'image/gif', 'image/jpg', 'image/jpeg', 'image/png', 'image/svg+xml', 'image/tiff',
        'image/webp', 'image/bmp', 'image/vnd.microsoft.icon'
    )
    MAX_FILE_SIZE = 50 * 1024 * 1024  # MB

    class FOR_CHOICES(enum.Enum):
        ENTRY = 0
        COMMUNICATION = 1
        CONTEXTUAL_UPDATE = 2

    attachment = CachedFileField(
        verbose_name=_('Attachment'),
        blank=False,
        null=False,
        upload_to=global_upload_to,
        max_length=2000,
    )
    attachment_for = enum.EnumField(enum=FOR_CHOICES, verbose_name=_('Attachment for'),
                                    null=True, blank=True,
                                    help_text=_('The type of instance for which attachment was'
                                                ' uploaded for'))
    mimetype = models.CharField(verbose_name=_('Mimetype'), max_length=256,
                                blank=True, null=True)
    encoding = models.CharField(verbose_name=_('Encoding'), max_length=256,
                                blank=True, null=True)
    filetype_detail = models.CharField(verbose_name=_('File type detail'), max_length=2000,
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
    class PREVIEW_STATUS(enum.Enum):
        PENDING = 0
        COMPLETED = 1
        FAILED = 2
        IN_PROGRESS = 3
        KILLED = 4

        __labels__ = {
            PENDING: _("Pending"),
            COMPLETED: _("Completed"),
            FAILED: _("Failed"),
            IN_PROGRESS: _("In Progress"),
            KILLED: _("Killed"),
        }

    url = models.URLField(verbose_name=_('Source URL'), max_length=2000)
    token = models.CharField(verbose_name=_('Token'),
                             max_length=64, db_index=True,
                             blank=True, null=True)
    pdf = CachedFileField(
        verbose_name=_('Rendered Pdf'),
        blank=True,
        null=True,
        upload_to=global_upload_to,
        max_length=2000,
    )
    status = enum.EnumField(enum=PREVIEW_STATUS, default=PREVIEW_STATUS.PENDING)
    remark = models.TextField(verbose_name=_('Remark'),
                              blank=True, null=True)

    @classmethod
    def get_pdf(cls, data: dict, instance: 'SourcePreview' = None) -> 'SourcePreview':
        """
        Based on the url, generate a pdf and store it.
        """
        url = data['url']
        created_by = data.get('created_by')
        last_modified_by = data.get('last_modified_by')
        if not instance:
            token = str(uuid.uuid4())
            instance = cls(token=token)
        instance.url = url
        instance.created_by = created_by
        instance.last_modified_by = last_modified_by
        instance.save()

        transaction.on_commit(lambda: generate_pdf.delay(
            instance.pk
        ))
        return instance


def excel_upload_to(instance, filename: str) -> str:
    return f'contrib/excel/{uuid4()}/{instance.download_type}/{filename}'


class ExcelDownload(MetaInformationAbstractModel):
    class EXCEL_GENERATION_STATUS(enum.Enum):
        PENDING = 0
        IN_PROGRESS = 1
        COMPLETED = 2
        FAILED = 3
        KILLED = 4

    class DOWNLOAD_TYPES(enum.Enum):
        CRISIS = 0
        EVENT = 1
        COUNTRY = 2
        ENTRY = 3
        FIGURE = 4
        ORGANIZATION = 5
        CONTACT = 6
        REPORT = 7
        ACTOR = 8
        INDIVIDUAL_REPORT = 9
        TRACKING_DATA = 10

    started_at = models.DateTimeField(
        verbose_name=_('Started at'),
        blank=True,
        null=True,
    )
    completed_at = models.DateTimeField(
        verbose_name=_('Completed at'),
        blank=True,
        null=True,
    )
    download_type = enum.EnumField(
        DOWNLOAD_TYPES,
        null=False,
        blank=False,
    )
    status = enum.EnumField(
        EXCEL_GENERATION_STATUS,
        default=EXCEL_GENERATION_STATUS.PENDING,
    )
    file = CachedFileField(
        verbose_name=_('Excel File'),
        blank=True,
        null=True,
        upload_to=excel_upload_to,
        max_length=2000,
    )
    file_size = models.IntegerField(
        verbose_name=_('File Size'),
        blank=True,
        null=True,
    )
    filters = JSONField(
        verbose_name=_('Filters'),
        blank=True,
        null=True,
    )

    def get_model_sheet_data_getter(self):
        mapper = {
            self.DOWNLOAD_TYPES.CRISIS: apps.get_model('crisis', 'Crisis'),
            self.DOWNLOAD_TYPES.EVENT: apps.get_model('event', 'Event'),
            self.DOWNLOAD_TYPES.COUNTRY: apps.get_model('country', 'Country'),
            self.DOWNLOAD_TYPES.ENTRY: apps.get_model('entry', 'Entry'),
            self.DOWNLOAD_TYPES.FIGURE: apps.get_model('entry', 'Figure'),
            self.DOWNLOAD_TYPES.ORGANIZATION: apps.get_model('organization', 'Organization'),
            self.DOWNLOAD_TYPES.CONTACT: apps.get_model('contact', 'Contact'),
            self.DOWNLOAD_TYPES.REPORT: apps.get_model('report', 'Report'),
            self.DOWNLOAD_TYPES.ACTOR: apps.get_model('event', 'Actor'),
            self.DOWNLOAD_TYPES.INDIVIDUAL_REPORT: apps.get_model('report', 'Report'),
            self.DOWNLOAD_TYPES.TRACKING_DATA: apps.get_model('contrib', 'ClientTrackInfo'),
        }
        model = mapper.get(self.download_type)
        if not model:
            raise AttributeError(f'Excel mapper cannot find model={model.name} in mapping.')
        if not hasattr(model, 'get_excel_sheets_data'):
            raise AttributeError(f'Excel sheet data getter missing for {model.name}')
        return model.get_excel_sheets_data

    def trigger_excel_generation(self, request, model_instance_id=None):
        '''
        This should trigger the excel file generation based on the
        given request. Filters are preserved within the instance.

        Is called by serializer.create method
        '''
        transaction.on_commit(lambda: generate_excel_file.delay(
            self.pk, request.user.id, model_instance_id=model_instance_id
        ))


class Client(MetaInformationAbstractModel):
    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=100,
        help_text=_('Recommended format client-short-name:custom-name:month:day'),
        unique=True
    )
    is_active = models.BooleanField(
        verbose_name=_('Is active?'),
        default=False
    )

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        client_ids = list(Client.objects.values_list('code', flat=True))
        set_client_ids_in_redis(client_ids)
        return instance

    def delete(self, *args, **kwargs):
        deleted = super().delete(*args, **kwargs)
        client_ids = list(Client.objects.values_list('code', flat=True))
        set_client_ids_in_redis(client_ids)
        return deleted


class ClientTrackInfo(models.Model):
    from apps.entry.models import ExternalApiDump
    client = models.ForeignKey('Client', on_delete=models.CASCADE)
    api_type = models.CharField(
        max_length=40,
        choices=ExternalApiDump.ExternalApiType.choices,
    )
    requests_per_day = models.IntegerField()
    tracked_date = models.DateField()

    class Meta:
        unique_together = ('client', 'api_type', 'tracked_date')

    def __str__(self):
        return f'{self.client} - {self.tracked_date}'

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.entry.models import ExternalApiDump
        from .filters import ClientTrackInfoFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            client_name='Client Name',
            client_code='Client Code',
            api_type='Api Type',
            api_name='Api Name',
            tracked_date='Date',
            requests_per_day='Requests',
        )
        data = ClientTrackInfoFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            client_name=models.F('client__name'),
            client_code=models.F('client__code'),
            api_name=models.F('api_type'),
        ).order_by('-tracked_date')

        def transformer(datum):
            return {
                **datum,
                'api_name': getattr(ExternalApiDump.ExternalApiType(datum['api_type']), 'label', ''),
            }
        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': transformer,
        }

    @classmethod
    def annotate_api_name(cls):
        from apps.entry.models import ExternalApiDump
        return {
            'api_name': models.Case(
                *[
                    models.When(
                        api_type=enum_obj.value,
                        then=models.Value(enum_obj.label, output_field=models.CharField())
                    ) for enum_obj in ExternalApiDump.ExternalApiType
                ]
            )
        }
