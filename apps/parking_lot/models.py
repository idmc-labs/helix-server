from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
from django.contrib.postgres.fields import JSONField

from apps.contrib.models import MetaInformationAbstractModel


class ParkedItem(MetaInformationAbstractModel):
    class PARKING_LOT_STATUS(enum.Enum):
        TO_BE_REVIEWED = 0
        REVIEWED = 1
        ON_GOING = 2

        __labels__ = {
            TO_BE_REVIEWED: _('To be reviewed'),
            REVIEWED: _('Reviewed'),
            ON_GOING: _('On going'),
        }

    class PARKING_LOT_SOURCE(enum.Enum):
        IDETECT = 0
        HAZARD_MONITORING = 1
        ACLED = 2

        __labels__ = {
            IDETECT: _('Idetect'),
            HAZARD_MONITORING: _('Hazard Monitoring'),
            ACLED: _('Acled')
        }

    country = models.ForeignKey(
        'country.Country',
        verbose_name=_('Country'),
        related_name='parked_items',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    title = models.TextField(verbose_name=_('Title'))
    url = models.URLField(verbose_name=_('URL'), max_length=2000)
    assigned_to = models.ForeignKey('users.User', verbose_name=_('Assigned To'),
                                    related_name='assigned_parked_items',
                                    on_delete=models.SET_NULL,
                                    blank=True, null=True)
    status = enum.EnumField(PARKING_LOT_STATUS, verbose_name=_('Status'),
                            default=PARKING_LOT_STATUS.TO_BE_REVIEWED)
    comments = models.TextField(verbose_name=_('Comments'),
                                blank=True, null=True)
    source = enum.EnumField(PARKING_LOT_SOURCE, verbose_name=_('Source'),
                            blank=True, null=True)
    source_uuid = models.CharField(verbose_name=_('Source Uuid'),
                                   max_length=255, blank=True, null=True)
    meta_data = JSONField(blank=True, null=True, default=None)

    def move_to_entry(self):
        ...  # TODO?

    def __str__(self):
        return f'{self.country.name}- {self.title}'
