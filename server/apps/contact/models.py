from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel


class Contact(MetaInformationArchiveAbstractModel, models.Model):
    class DESIGNATION(enum.Enum):
        MR = 0
        MS = 1

        __labels__ = {
            MR: _("Mr"),
            MS: _("Ms"),
        }

    class GENDER(enum.Enum):
        MALE = 0
        FEMALE = 1
        OTHER = 2

        __labels__ = {
            MALE: _("Male"),
            FEMALE: _("Female"),
            OTHER: _("Other"),
        }

    designation = enum.EnumField(DESIGNATION)
    first_name = models.CharField(verbose_name=_('First Name'), max_length=256)
    last_name = models.CharField(verbose_name=_('Last Name'), max_length=256)
    gender = enum.EnumField(GENDER, verbose_name=_('Gender'))
    job_title = models.CharField(verbose_name=_('Job Title'), max_length=256)
    organization = models.ForeignKey('organization.Organization', verbose_name=_('Organization'),
                                     related_name='contacts', on_delete=models.CASCADE)
    countries_of_operation = models.ManyToManyField('country.Country',
                                                    verbose_name=_('Countries of Operation'),
                                                    blank=True,
                                                    related_name='operating_contacts',
                                                    help_text=_(
                                                        'In which countries does this contact person'
                                                        ' operate?'
                                                    ))
    country = models.ForeignKey('country.Country',
                                verbose_name=_('Country'),
                                blank=True, null=True,
                                related_name='contacts', on_delete=models.SET_NULL)
    email = models.EmailField(verbose_name=_('Email'), blank=True, null=True)
    phone = models.CharField(verbose_name=_('Phone'), max_length=32,
                             blank=True, null=True,
                             unique=True)
    comment = models.TextField(verbose_name=_('Comment'), blank=True, null=True)

    def __str__(self):
        return f'{self.designation.name} {self.first_name} {self.last_name}'

    @property
    def full_name(self):
        return f'{self.designation.name} {self.first_name} {self.last_name}'


class CommunicationMedium(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    def __str__(self):
        return f'{self.name}'


class Communication(MetaInformationArchiveAbstractModel, models.Model):
    class COMMUNICATION_MEDIUM(enum.Enum):
        pass

    contact = models.ForeignKey('Contact', verbose_name=_('Contact'),
                                related_name='communications', on_delete=models.CASCADE)
    title = models.CharField(verbose_name=_('Title'), max_length=256,
                             blank=True, null=True)
    subject = models.CharField(verbose_name=_('Subject'), max_length=512)
    content = models.TextField(verbose_name=_('Content'))
    date_time = models.DateTimeField(verbose_name=_('Date'),
                                     null=True, blank=True,
                                     help_text=_('Date on which communication occurred.'))
    medium = models.ForeignKey(CommunicationMedium,
                               null=True, blank=False,
                               related_name='+', on_delete=models.SET_NULL)
    attachment = models.ForeignKey('contrib.Attachment', verbose_name='Attachment',
                                   on_delete=models.CASCADE, related_name='+',
                                   null=True, blank=True)

    def __str__(self):
        return f'{self.contact} {self.date_time}'
